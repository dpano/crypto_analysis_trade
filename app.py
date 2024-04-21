from flask import Flask, request
from flask_restful import Resource, Api
import sqlite3

from api.resources.orders import OrderById, OrderList
from api.resources.signals import SignalList
from db.database import connect_db, get_db_cursor
from helpers.data_manipulation import current_datetime

app = Flask(__name__)
api = Api(app)


class PositionsById(Resource):
    # Implement CRUD methods for Position similar to Order
    def get(self, position_id):
        conn = get_db_cursor()
        order = conn.execute('SELECT * FROM positions WHERE id = ?', 
                             (position_id,)).fetchone()
        conn.close()
        if order is None:
            return {'message': 'Position not found'}, 404
        return dict(order)

class PositionsList(Resource):
    # Implement CRUD methods for Position similar to Order
    def get(self):
        conn = get_db_cursor()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM positions")
        positions = cursor.fetchall()
        conn.close()

        # Convert rows to a list of dicts
        positions_list = [dict(order) for order in positions]

        return positions_list
    
    def post(self):
        data = request.get_json()
        
        conn = get_db_cursor()
        cursor = conn.cursor()
        
        cursor.execute(""" 
                       INSERT INTO positions (status,quantity,symbol,create_timestamp) VALUES (?,?,?,?)
                       """, (data['status'],data.get('quantity'),data['symbol'],current_datetime()))
        conn.commit()
        position_id = cursor.lastrowid
        conn.close()

        return {'message': 'Position created', 'position_id': position_id}, 201

api.add_resource(OrderById, '/orders/<int:order_id>')
api.add_resource(OrderList, '/orders')
api.add_resource(SignalList, '/signals')
api.add_resource(PositionsList, '/positions')
    # Add the Position resource similarly

if __name__ == '__main__':
    app.run(debug=True)
