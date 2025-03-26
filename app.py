from src.app.cover_letter_app import CoverLetterApp
import warnings

def main():
    """Main function to run the application"""
    # Filter out specific Gradio warnings about argument mismatches
    warnings.filterwarnings("ignore", category=UserWarning, module="gradio.utils")
    
    app = CoverLetterApp()
    demo = app.build_ui()
    demo.launch(share=False, debug=True)

if __name__ == "__main__":
    main()