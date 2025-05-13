try:
    from app import main
    print("App imported successfully. Basic structure seems OK.")
except ImportError as e:
    print(f"Error importing app: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

