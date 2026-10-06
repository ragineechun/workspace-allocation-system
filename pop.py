from website import db, create_app

app = create_app()

with app.app_context():
    db.drop_all()  # Drop old tables
    db.create_all()  # Create new tables
