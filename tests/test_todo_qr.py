import asyncio
import unittest
from ziriziri.renderer import render_todo_receipt, make_todo_qr, wrap_text
from ziriziri.config import PRINTER_WIDTH
from ziriziri.server import TodoItem, TodoRequest, preview_todo


class TestTodoQR(unittest.TestCase):
    def test_make_todo_qr_dimensions(self):
        """Verify QR code fits within thermal item bounds."""
        img = make_todo_qr("https://camp-fire.jp/projects/view/123456", max_size=115)
        self.assertLessEqual(img.width, 115)
        self.assertLessEqual(img.height, 115)
        self.assertEqual(img.mode, "1")

        img_memo = make_todo_qr("E26 60W 昼白色", max_size=115)
        self.assertLessEqual(img_memo.width, 115)
        self.assertLessEqual(img_memo.height, 115)

    def test_wrap_text(self):
        """Verify Japanese text wrapping."""
        from ziriziri.renderer import get_font
        font = get_font(16)
        lines = wrap_text("あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほ", font, max_width=100)
        self.assertGreater(len(lines), 1)

    def test_render_todo_receipt_with_qr(self):
        """Verify receipt dimensions and thermal head even-line constraint."""
        items = [
            {"text": "通常アイテム (QRなし)", "checked": False},
            {
                "text": "クラファン支援品",
                "checked": False,
                "qr_type": "url",
                "qr_data": "https://camp-fire.jp/projects/view/123456",
            },
            {
                "text": "成城石井 本店",
                "checked": True,
                "qr_type": "map",
                "qr_data": "https://maps.app.goo.gl/abcdef",
            },
            {
                "text": "LED電球 密閉器具対応 E26 60W相当 昼白色",
                "checked": False,
                "qr_type": "memo",
                "qr_data": "E26 60W 810lm 昼白色 密閉型",
            },
        ]

        img = render_todo_receipt(title="お買い物リスト", items=items)
        self.assertEqual(img.width, PRINTER_WIDTH)
        self.assertEqual(img.height % 2, 0)  # Thermal head 2-line chunk constraint
        self.assertEqual(img.mode, "1")

    def test_preview_todo_endpoint(self):
        """Verify preview_todo FastAPI endpoint response format."""
        async def run_async():
            req = TodoRequest(
                title="テストリスト",
                items=[
                    TodoItem(text="たまご", checked=False),
                    TodoItem(
                        text="お店の場所",
                        checked=False,
                        qr_type="map",
                        qr_data="https://maps.app.goo.gl/test",
                    ),
                ],
                show_datetime=True,
                datetime_position="header",
                show_cut_line=True,
            )
            return await preview_todo(req)

        res = asyncio.run(run_async())
        self.assertIn("preview", res)
        self.assertTrue(res["preview"].startswith("data:image/png;base64,"))
        self.assertEqual(res["height"] % 2, 0)


if __name__ == "__main__":
    unittest.main()
