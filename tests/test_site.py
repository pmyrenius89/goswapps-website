"""Dependency-free checks for the site's publishing and privacy contract."""

from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import re
import struct
import unittest
from urllib.parse import unquote, urljoin, urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://goswapps.com/"


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.elements = []
        self.ids = []
        self.text = []
        self.feed(path.read_text())

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.elements.append((tag, attributes))
        if "id" in attributes:
            self.ids.append(attributes["id"])

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_data(self, data):
        self.text.append(data)

    def find(self, tag):
        return [attrs for element, attrs in self.elements if element == tag]


class SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = {path.name: Page(path) for path in ROOT.glob("*.html")}

    def test_semantic_landmarks_and_language(self):
        self.assertEqual(set(self.pages), {"index.html", "privacy.html", "404.html"})
        for filename, page in self.pages.items():
            with self.subTest(page=filename):
                self.assertEqual(page.find("html")[0]["lang"], "en")
                for landmark in ("main", "header", "footer", "h1", "title"):
                    self.assertEqual(len(page.find(landmark)), 1, landmark)
                self.assertTrue(page.find("nav")[0].get("aria-label"))
                self.assertIn("#main", [a.get("href") for a in page.find("a")])
                self.assertFalse([key for key, count in Counter(page.ids).items() if count > 1])

    def test_links_and_local_assets_resolve(self):
        for filename, page in self.pages.items():
            for tag, attrs in page.elements:
                for attr in ("href", "src"):
                    if attr not in attrs:
                        continue
                    value = attrs[attr]
                    with self.subTest(page=filename, tag=tag, link=value):
                        self.assertTrue(value)
                        parsed = urlsplit(urljoin(ORIGIN + filename, value))
                        if parsed.scheme == "mailto":
                            self.assertIn(parsed.path, ("hello@goswapps.com", "support@goswapps.com"))
                            continue
                        self.assertEqual(parsed.scheme, "https")
                        if parsed.netloc != "goswapps.com":
                            self.assertEqual(tag, "a", "Resources must be served locally")
                            self.assertEqual(parsed.netloc, "docs.github.com")
                            continue
                        target = ROOT / (unquote(parsed.path).lstrip("/") or "index.html")
                        self.assertTrue(target.is_file(), target)
                        if parsed.fragment:
                            self.assertIn(parsed.fragment, self.pages[target.name].ids)

    def test_no_executable_or_third_party_features(self):
        forbidden = {"script", "iframe", "object", "embed", "form", "input", "video", "audio", "base"}
        for filename, page in self.pages.items():
            with self.subTest(page=filename):
                self.assertFalse(forbidden.intersection(tag for tag, _ in page.elements))
                for tag, attrs in page.elements:
                    self.assertFalse(any(name.startswith("on") for name in attrs), tag)
                    self.assertFalse({"srcset", "ping", "srcdoc"}.intersection(attrs))
                    self.assertNotEqual(attrs.get("http-equiv", "").lower(), "refresh")
                    if tag == "link":
                        self.assertNotIn(attrs.get("rel"), ("preconnect", "dns-prefetch", "prefetch"))
        css = (ROOT / "styles.css").read_text()
        self.assertNotRegex(css, r"(?i)@import|url\s*\(|expression\s*\(")

    def test_search_and_social_metadata(self):
        for filename in ("index.html", "privacy.html"):
            page = self.pages[filename]
            with self.subTest(page=filename):
                meta = {a.get("name", a.get("property")): a.get("content") for a in page.find("meta")}
                for key in ("description", "og:type", "og:title", "og:description", "og:url", "og:image", "og:image:alt", "twitter:card"):
                    self.assertTrue(meta.get(key), key)
                canonical = [a["href"] for a in page.find("link") if a.get("rel") == "canonical"]
                expected = ORIGIN if filename == "index.html" else ORIGIN + filename
                self.assertEqual(canonical, [expected])
                self.assertEqual(meta["og:url"], expected)
                self.assertEqual(meta["og:image"], ORIGIN + "assets/social-card.png")
                self.assertIn("width=device-width", meta["viewport"])
                self.assertNotIn("maximum-scale", meta["viewport"])
                self.assertNotIn("user-scalable", meta["viewport"])
        self.assertIn({"name": "robots", "content": "noindex"}, self.pages["404.html"].find("meta"))

    def test_verified_product_descriptions_and_statuses(self):
        text = " ".join(" ".join(self.pages["index.html"].text).split())
        for fact in ("MindReset", "A calm and focus app.", "App Store review pending", "ActionBridge", "Turn shared screenshots and notes into Calendar events and Reminders.", "Hush", "An overnight snoring recording app."):
            self.assertIn(fact, text)
        self.assertEqual(text.count("In development"), 2)
        self.assertIn("not available to download yet", text)
        self.assertNotRegex(text, r"(?i)download (now|on)|available (now|today)|\btestimonials?\b|\b\d[\d,]* (users|downloads|customers)\b")
        self.assertFalse(any("apps.apple.com" in a.get("href", "") for a in self.pages["index.html"].find("a")))

    def test_sitemap_and_robots(self):
        root = ET.parse(ROOT / "sitemap.xml").getroot()
        locations = [el.text for el in root.findall("{*}url/{*}loc")]
        self.assertCountEqual(locations, [ORIGIN, ORIGIN + "privacy.html"])
        self.assertIn("Sitemap: " + ORIGIN + "sitemap.xml", (ROOT / "robots.txt").read_text())
        self.assertTrue((ROOT / ".nojekyll").is_file())
        self.assertFalse((ROOT / "CNAME").exists(), "Domain configuration requires separate approval")
        self.assertFalse((ROOT / ".github/workflows").exists(), "No automatic publishing workflow")

    def test_image_formats_and_dimensions(self):
        for filename, expected in (("social-card.png", (1200, 630)), ("favicon.png", (32, 32)), ("apple-touch-icon.png", (180, 180))):
            with self.subTest(image=filename):
                data = (ROOT / "assets" / filename).read_bytes()
                self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
                self.assertEqual(struct.unpack(">II", data[16:24]), expected)
        for path in (ROOT / "assets").glob("*.svg"):
            root = ET.parse(path).getroot()
            self.assertTrue(root.tag.endswith("svg"))
            for element in root.iter():
                self.assertNotIn(element.tag.split("}")[-1], ("script", "foreignObject", "image"))
                self.assertFalse(any(key.startswith("on") or "href" in key for key in element.attrib))

    def test_public_contacts_only(self):
        for filename, page in self.pages.items():
            with self.subTest(page=filename):
                text = " ".join(page.text)
                addresses = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
                self.assertLessEqual(set(addresses), {"hello@goswapps.com", "support@goswapps.com"})
                self.assertFalse(any(a.get("href", "").startswith("tel:") for a in page.find("a")))


if __name__ == "__main__":
    unittest.main()
