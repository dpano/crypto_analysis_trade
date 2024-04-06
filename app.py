from flask import Flask, request
from flask_restful import Resource, Api
import sqlite3

from db.database import connect_db
from helpers.data_manipulation import current_datetime

app = Flask(__name__)
api = Api(app)

def get_db_connection():
    conn = connect_db()
    conn.row_factory = sqlite3.Row
    return conn

class OrderById(Resource):
    def get(self, order_id):
        conn = get_db_connection()
        order = conn.execute('SELECT * FROM orders WHERE id = ?', 
                             (order_id,)).fetchone()
        conn.close()
        if order is None:
            return {'message': 'Order not found'}, 404
        return dict(order)

    def delete(self, order_id):
        conn = get_db_connection()
        conn.execute('DELETE FROM orders WHERE id = ?', (order_id,))
        conn.commit()
        conn.close()
        return '', 204

    def put(self, order_id):
        conn = get_db_connection()
        data = request.get_json()
        conn.execute('UPDATE orders SET status = ? WHERE id = ?', 
                     (data['status'], order_id))
        conn.commit()
        conn.close()
        return {'message': 'Order updated successfully'}

class OrderList(Resource):
    def get(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders")
        orders = cursor.fetchall()
        conn.close()

        # Convert rows to a list of dicts
        orders_list = [dict(order) for order in orders]

        return orders_list
    
    def post(self):
        data = request.get_json()

        # Validate input data (this is a basic validation, consider using libraries like Marshmallow for more comprehensive validation)
        if not data or 'type' not in data or 'status' not in data:
            return {'message': 'Missing required fields'}, 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO orders (position_id, type, status, price, quantity, symbol, creation_timestamp, execution_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (data.get('position_id'), data['type'], data['status'], data.get('price'), data.get('quantity'), data['symbol'], data['creation_timestamp'], data.get('execution_timestamp')))

        conn.commit()
        order_id = cursor.lastrowid
        conn.close()

        return {'message': 'Order created', 'order_id': order_id}, 201

class PositionsById(Resource):
    # Implement CRUD methods for Position similar to Order
    def get(self, position_id):
        conn = get_db_connection()
        order = conn.execute('SELECT * FROM positions WHERE id = ?', 
                             (position_id,)).fetchone()
        conn.close()
        if order is None:
            return {'message': 'Position not found'}, 404
        return dict(order)

class PositionsList(Resource):
    # Implement CRUD methods for Position similar to Order
    def get(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM positions")
        positions = cursor.fetchall()
        conn.close()

        # Convert rows to a list of dicts
        positions_list = [dict(order) for order in positions]

        return positions_list
    
    def post(self):
        data = request.get_json()
        
        conn = get_db_connection()
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
api.add_resource(PositionsList, '/positions')
    # Add the Position resource similarly

if __name__ == '__main__':
    app.run(debug=True)
