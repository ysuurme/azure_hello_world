import os
import subprocess
import tempfile
from typing import TYPE_CHECKING

from src.config import D2_BINARY_PATH
from src.utils.m_log import f_log

if TYPE_CHECKING:
    from src.utils.m_diagram_style import DiagramStyle


class DiagramEngine:
    """
    Safely executes the D2 binary via standard library subprocesses to render Architectures.
    """

    def __init__(self, binary_path: str = None) -> None:
        self.binary_path = binary_path or D2_BINARY_PATH

    def generate_svg(self, d2_syntax: str, style: "DiagramStyle | None" = None) -> bytes | None:
        """
        Takes raw .d2 syntactical mapping, applies the standard's render config (sketch/theme/pad),
        compiles it, and returns the SVG bytes. The class preamble is composed into d2_syntax by the
        caller (so the stored/downloaded .d2 is self-contained); this method renders it as-is.
        """
        from src.utils.m_diagram_style import get_diagram_style

        style = style or get_diagram_style()
        f_log("Compiling D2 syntax to SVG via local binary.", level="process")

        # Use a secure temporary directory native to python
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = os.path.join(tmpdir, "architecture.d2")
            output_file = os.path.join(tmpdir, "architecture.svg")

            with open(input_file, "w", encoding="utf-8") as f:
                f.write(d2_syntax)

            try:
                args = [self.binary_path]
                if style.sketch:
                    args.append("--sketch")
                if style.theme is not None:
                    args += ["--theme", str(style.theme)]
                args += ["--pad", str(style.pad), input_file, output_file]
                # Standard library boundary: invoke the static binary
                subprocess.run(args, capture_output=True, text=True, check=True)

                with open(output_file, "rb") as f:
                    svg_bytes = f.read()

                f_log("SVG compiled successfully.", level="success")
                return svg_bytes

            except subprocess.CalledProcessError as e:
                f_log(f"D2 compilation failed: {e.stderr}", level="error")
                return None
            except FileNotFoundError:
                f_log("D2 binary not found. Ensure it is mapped in the Dockerfile.", level="error")
                return None
