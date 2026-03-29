import pytest
from unittest.mock import patch, mock_open
from src.utils.m_diagram_engine import DiagramEngine

@patch('src.utils.m_diagram_engine.subprocess.run')
@patch('builtins.open', new_callable=mock_open, read_data=b'<svg>Mock Architecture</svg>')
def test_static_diagram_subprocess_arguments(mock_file, mock_subprocess):
    """
    Ensure the python subprocess safely maps arguments natively against the GO binary.
    Bypasses real compilation to avoid local host dependency clashes during CI/CD.
    """
    mock_subprocess.return_value.returncode = 0
    
    engine = DiagramEngine(binary_path="d2")
    markup = "sys: Server"
    
    result_bytes = engine.generate_svg(markup)
    
    # Assert successful SVGs retrieval (bytes)
    assert result_bytes == b'<svg>Mock Architecture</svg>'
    
    # Verify subprocess called the compiler correctly natively
    mock_subprocess.assert_called_once()
    
    # Extract the precise command args sent to OS via subprocess
    args = mock_subprocess.call_args[0][0]
    
    # Argument 0 is the binary declaration
    assert args[0] == "d2"
    # Arguments 1 and 2 map dynamically to internal temporal directories 
    assert "architecture.d2" in args[1]
    assert "architecture.svg" in args[2]
