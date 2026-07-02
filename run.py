from app import create_app


# create_app() is the single application entry point: it owns all extension
# initialisation (db, migrate). This module only constructs and runs the app.
app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
