import pytest
from streamlit.testing.v1 import AppTest

class TestUITopology:

    @pytest.fixture
    def app_test(self):
        """Initializes the Streamlit AppTest framework for Headless UI validation."""
        at = AppTest.from_file("src/ui/app.py")
        return at

    def test_app_instantiation_and_layout(self, app_test):
        """
        Verify that the Streamlit application Native MVP loads without structural HTTP dependency errors.
        Ensures the sidebar and primary titles are properly configured.
        """
        app_test.run(timeout=10)
        
        # Verify app didn't crash during initialization
        assert not app_test.exception
        
        # Verify Headers
        assert app_test.title[0].value == "Architecture Agent 🛡️"
        assert app_test.markdown[0].value == "### Technical Design Authority Agent"
        
        # Verify Sidebar Configuration
        assert app_test.sidebar.info[0].value == "Running Lean MVP locally with direct orchestrator bindings."
        
    def test_app_session_reset(self, app_test):
        """
        Verify the reset button properly restores session history bounds.
        """
        app_test.run(timeout=10)
        assert len(app_test.session_state["chat_history"]) == 1
        
        # Simulate typing a query
        app_test.chat_input[0].set_value("Analyze App Service").run()
        
        # History should increase (User Message + Model Spinner/Response)
        assert len(app_test.session_state["chat_history"]) > 1
        
        # Simulate pressing Reset
        app_test.sidebar.button[0].click().run()
        
        # History length should revert to 1 (The welcome message)
        assert len(app_test.session_state["chat_history"]) == 1
