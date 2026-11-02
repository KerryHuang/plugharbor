import json, pathlib, subprocess, sys, tempfile, unittest

from PIL import Image

HERE = pathlib.Path(__file__).parent
SCRIPT = HERE / "annotate.py"
WHITE = (255, 255, 255)
RED = (217, 48, 37)
BG = (52, 103, 169)


def run(tmp, base_color, ops, extra=None, paint=None):
    base = tmp / "base.png"
    out = tmp / "out.png"
    img = Image.new("RGB", (100, 100), base_color)
    if paint:
        paint(img)
    img.save(base)
    spec = {"base": str(base), "output": str(out), "ops": ops, **(extra or {})}
    sp = tmp / "spec.json"
    sp.write_text(json.dumps(spec), encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPT), str(sp)], capture_output=True, text=True)
    return r, out


class AnnotateTest(unittest.TestCase):
    def test_rect_draws_red_border_and_leaves_rest(self):
        with tempfile.TemporaryDirectory() as t:
            r, out = run(pathlib.Path(t), WHITE, [{"op": "rect", "box": [10, 10, 30, 30], "color": "red", "width": 4}])
            self.assertEqual(r.returncode, 0, r.stderr)
            px = Image.open(out).convert("RGB")
            self.assertEqual(px.getpixel((10, 10)), RED)
            self.assertEqual(px.getpixel((50, 50)), WHITE)

    def test_mask_matches_surrounding_background(self):
        def paint(img):  # 框內放一塊「個資」色塊，周圍是純色底
            for x in range(35, 55):
                for y in range(40, 55):
                    img.putpixel((x, y), (0, 0, 0))
        with tempfile.TemporaryDirectory() as t:
            r, out = run(pathlib.Path(t), BG, [{"op": "mask", "box": [30, 30, 70, 70]}], paint=paint)
            self.assertEqual(r.returncode, 0, r.stderr)
            px = Image.open(out).convert("RGB")
            self.assertEqual(px.getpixel((40, 45)), BG)  # 原本是黑色塊
            self.assertEqual(px.getpixel((40, 45)), px.getpixel((5, 5)))

    def test_mask_explicit_color(self):
        with tempfile.TemporaryDirectory() as t:
            r, out = run(pathlib.Path(t), WHITE, [{"op": "mask", "box": [30, 30, 70, 70], "color": [1, 2, 3]}])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(Image.open(out).convert("RGB").getpixel((50, 50)), (1, 2, 3))

    def test_unknown_op_fails(self):
        with tempfile.TemporaryDirectory() as t:
            r, _ = run(pathlib.Path(t), WHITE, [{"op": "nope"}])
            self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
