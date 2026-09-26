import io

from app import create_app, db
from app.models import Product

app = create_app()
app.config['TESTING'] = True

with app.app_context():
    db.drop_all()
    db.create_all()

with app.test_client() as client:
    response = client.post('/login', data={'login_input': 'admin', 'password': 'admin123'}, follow_redirects=False)
    print('login_status', response.status_code)
    print('login_location', response.headers.get('Location'))

    csv_data = b'name,sku,category,unit_of_measure,location,initial_stock,reorder_level\nSteel Pipe,STP-100,Raw Material,kg,Main Warehouse,42,15\nDesk Lamp,DL-200,Furniture,pieces,Rack A,8,6\n'
    response = client.post('/products/upload-csv', data={'file': (io.BytesIO(csv_data), 'inventory.csv')}, follow_redirects=True)
    print('upload_status', response.status_code)
    print('skus_found', Product.query.filter_by(sku='STP-100').count(), Product.query.filter_by(sku='DL-200').count())
