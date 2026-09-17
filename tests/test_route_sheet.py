import asyncio
import unittest
from ziriziri.config import PRINTER_WIDTH
from ziriziri.renderer import build_gmaps_url, render_route_sheet
from ziriziri.server import RouteItem, RouteRequest, preview_route


class TestRouteSheet(unittest.TestCase):
    def test_build_gmaps_url(self):
        """Verify Google Maps URL structure for navigation and search modes."""
        # Navigation mode (default)
        url_nav = build_gmaps_url("熱海サンビーチ", travel_mode="driving", action="navigate")
        self.assertIn("https://www.google.com/maps/dir/?api=1", url_nav)
        self.assertIn("travelmode=driving", url_nav)
        self.assertIn("dir_action=navigate", url_nav)
        self.assertTrue("%E7%86%B1%E6%B5%B7" in url_nav or "destination=" in url_nav)

        # Walking navigation
        url_walk = build_gmaps_url("渋谷駅", travel_mode="walking", action="navigate")
        self.assertIn("travelmode=walking", url_walk)

        # Place search mode
        url_search = build_gmaps_url("大黒PA", action="search")
        self.assertIn("https://www.google.com/maps/search/?api=1&query=", url_search)

        # Empty destination fallback
        url_empty = build_gmaps_url("")
        self.assertEqual(url_empty, "https://www.google.com/maps")

    def test_render_route_sheet_dimensions(self):
        """Verify thermal printing constraints (width 384px, even line height)."""
        items = [
            {
                "name": "海老名SA",
                "location": "海老名SA 下り",
                "note": "09:30 集合・給油",
                "checked": True,
                "action": "navigate",
            },
            {
                "name": "芦ノ湖スカイライン フジビュー",
                "location": "芦ノ湖スカイライン",
                "note": "富士山を眺めながら休憩",
                "checked": False,
                "action": "navigate",
            },
            {
                "name": "修善寺温泉 街歩き",
                "location": "修善寺温泉",
                "note": "名物温泉まんじゅう",
                "checked": False,
                "action": "search",
            },
        ]

        img = render_route_sheet(
            title="🚗 伊豆ドライブ旅",
            items=items,
            travel_mode="driving",
            show_cut_line=True,
        )

        self.assertEqual(img.width, PRINTER_WIDTH)
        self.assertEqual(img.height % 2, 0)
        self.assertEqual(img.mode, "1")

    def test_render_route_sheet_empty_items(self):
        """Verify empty route list does not crash and respects thermal constraints."""
        img = render_route_sheet(title="空のルート", items=[], show_cut_line=False)
        self.assertEqual(img.width, PRINTER_WIDTH)
        self.assertEqual(img.height % 2, 0)
        self.assertEqual(img.mode, "1")

    def test_preview_route_endpoint(self):
        """Verify FastAPI preview endpoint for route sheets."""
        async def run_async():
            req = RouteRequest(
                title="テストドライブルート",
                items=[
                    RouteItem(
                        name="東京タワー",
                        location="東京都港区芝公園4丁目2-8",
                        note="夜景観賞",
                        action="navigate",
                    )
                ],
                travel_mode="driving",
                show_cut_line=True,
            )
            return await preview_route(req)

        res = asyncio.run(run_async())
        self.assertIn("preview", res)
        self.assertTrue(res["preview"].startswith("data:image/png;base64,"))
        self.assertEqual(res["height"] % 2, 0)


    def test_render_route_sheet_inline_cut_and_pause(self):
        """Verify inline cut separators and pause points are generated every 2 spots."""
        items = [
            {"name": f"スポット {i}", "location": f"場所 {i}", "action": "navigate"}
            for i in range(1, 7)
        ]
        img = render_route_sheet(title="6スポット旅", items=items, show_cut_line=True)
        self.assertEqual(img.width, PRINTER_WIDTH)
        self.assertEqual(img.height % 2, 0)
        pause_chunks = img.info.get("pause_chunks", [])
        # For 6 items, pause points should be after item 2 and item 4 (2 cut points)
        self.assertEqual(len(pause_chunks), 2)
        self.assertEqual(pause_chunks[0]["finished_spots"], "01〜02")
        self.assertEqual(pause_chunks[1]["finished_spots"], "03〜04")


if __name__ == "__main__":
    unittest.main()
