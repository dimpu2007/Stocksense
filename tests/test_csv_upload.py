import io

from app import create_app, db
from app.models import Product
from app.seed import seed_demo_data


def test_csv_upload_imports_products():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        db.drop_all()
        db.create_all()
        seed_demo_data()

    with app.test_client() as client:
        login = client.post('/login', data={'login_input': 'admin', 'password': 'admin123'}, follow_redirects=False)
        assert login.status_code in (302, 303)

        csv_data = b'name,sku,category,unit_of_measure,location,initial_stock,reorder_level\nSteel Pipe,STP-100,Raw Material,kg,Main Warehouse,42,15\nDesk Lamp,DL-200,Furniture,pieces,Rack A,8,6\n'

        upload = client.post(
            '/products/upload-csv',
            data={'file': (io.BytesIO(csv_data), 'inventory.csv')},
            follow_redirects=True,
        )

        assert upload.status_code == 200

    with app.app_context():
        products = Product.query.all()
        assert len(products) >= 2
        assert Product.query.filter_by(sku='STP-100').first() is not None
