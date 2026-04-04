import os
import subprocess
import tempfile

from src.config import D2_BINARY_PATH
from src.utils.m_log import f_log


class DiagramEngine:
    """
    Safely executes the D2 binary via standard library subprocesses to render Architectures.
    """
    def __init__(self, binary_path: str = None) -> None:
        self.binary_path = binary_path or D2_BINARY_PATH
        
    def generate_svg(self, d2_syntax: str) -> bytes | None:
        """
        Takes raw .d2 syntactical mapping, compiles it, and returns the SVG bytes.
        """
        f_log("Compiling D2 syntax to SVG via local binary.", c_type="process")
        
        # Use a secure temporary directory native to python
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = os.path.join(tmpdir, "architecture.d2")
            output_file = os.path.join(tmpdir, "architecture.svg")
            
            with open(input_file, "w", encoding="utf-8") as f:
                f.write(d2_syntax)
                
            try:
                # Standard library boundary: invoke the static binary
                subprocess.run(
                    [self.binary_path, input_file, output_file],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                with open(output_file, "rb") as f:
                    svg_bytes = f.read()
                    
                f_log("SVG compiled successfully.", c_type="success")
                return svg_bytes
                
            except subprocess.CalledProcessError as e:
                f_log(f"D2 compilation failed: {e.stderr}", c_type="error")
                return None
            except FileNotFoundError:
                f_log("D2 binary not found. Ensure it is mapped in the Dockerfile.", c_type="error")
                return None
