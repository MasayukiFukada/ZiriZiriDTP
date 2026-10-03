import unittest
from PIL import Image
from ziriziri.config import PRINTER_WIDTH
from ziriziri.renderer import format_wifi_qr_data, render_wifi_card


class TestWifiRenderer(unittest.TestCase):
    def test_format_wifi_qr_data_wpa(self):
        qr_str = format_wifi_qr_data(ssid="MyHomeNetwork", password="SecretPassword123", security_type="WPA")
        self.assertEqual(qr_str, "WIFI:T:WPA;S:MyHomeNetwork;P:SecretPassword123;;")

    def test_format_wifi_qr_data_nopass(self):
        qr_str = format_wifi_qr_data(ssid="FreeWifi", security_type="nopass")
        self.assertEqual(qr_str, "WIFI:T:nopass;S:FreeWifi;;")

    def test_format_wifi_qr_data_hidden(self):
        qr_str = format_wifi_qr_data(ssid="StealthNet", password="pass", security_type="WPA", hidden=True)
        self.assertEqual(qr_str, "WIFI:T:WPA;S:StealthNet;P:pass;H:true;;")

    def test_format_wifi_qr_data_escaping(self):
        # Escape characters: \, ;, ,, :, "
        qr_str = format_wifi_qr_data(ssid="Shop;Net:1", password=r"my\secret;pass,word:1\"")
        self.assertIn(r"S:Shop\;Net\:1", qr_str)
        self.assertIn(r"P:my\\secret\;pass\,word\:1\\\"", qr_str)

    def test_render_wifi_card_dimensions_and_mode(self):
        img = render_wifi_card(
            ssid="CoffeeShop_Guest",
            password="espresso_latte",
            security_type="WPA",
            title="📶 カフェ Wi-Fi",
            note="ご自由にお使いください",
            show_cut_line=False,
        )
        self.assertEqual(img.mode, "1")
        self.assertEqual(img.width, PRINTER_WIDTH)
        self.assertEqual(img.height % 2, 0)

    def test_render_wifi_card_with_cut_line(self):
        img = render_wifi_card(
            ssid="Office-Guest",
            password="guestpassword",
            show_cut_line=True,
        )
        self.assertEqual(img.mode, "1")
        self.assertEqual(img.width, PRINTER_WIDTH)
        self.assertEqual(img.height % 2, 0)

    def test_render_wifi_card_nopass_and_datetime_header(self):
        img = render_wifi_card(
            ssid="Public-Open-Wifi",
            password="",
            security_type="nopass",
            show_datetime=True,
            datetime_position="header",
            hidden=True,
        )
        self.assertEqual(img.mode, "1")
        self.assertEqual(img.width, PRINTER_WIDTH)
        self.assertEqual(img.height % 2, 0)

    def test_server_preview_wifi(self):
        import asyncio
        from ziriziri.server import preview_wifi, WifiRequest

        req = WifiRequest(
            ssid="Test-Guest-Network",
            password="testpassword",
            security_type="WPA",
            show_cut_line=True,
        )
        res = asyncio.run(preview_wifi(req))
        self.assertIn("preview", res)
        self.assertTrue(res["preview"].startswith("data:image/png;base64,"))
        self.assertIn("height", res)
        self.assertEqual(res["height"] % 2, 0)


if __name__ == "__main__":
    unittest.main()
