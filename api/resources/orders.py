
from flask import request
from flask_restful import Resource

from db.database import get_db_cursor

class OrderById(Resource):
    def get(self, order_id):
        conn = get_db_cursor()
        order = conn.execute('SELECT * FROM orders WHERE id = ?', 
                             (order_id,)).fetchone()
        conn.close()
        if order is None:
            return {'message': 'Order not found'}, 404
        return dict(order)

    def delete(self, order_id):
        conn = get_db_cursor()
        conn.execute('DELETE FROM orders WHERE id = ?', (order_id,))
        conn.commit()
        conn.close()
        return '', 204

    def put(self, order_id):
        conn = get_db_cursor()
        data = request.get_json()
        conn.execute('UPDATE orders SET status = ? WHERE id = ?', 
                     (data['status'], order_id))
        conn.commit()
        conn.close()
        return {'message': 'Order updated successfully'}
    
class OrderList(Resource):
    def get(self):
        conn = get_db_cursor()
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

        conn = get_db_cursor()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO orders (position_id, type, status, price, quantity, symbol, creation_timestamp, execution_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (data.get('position_id'), data['type'], data['status'], data.get('price'), data.get('quantity'), data['symbol'], data['creation_timestamp'], data.get('execution_timestamp')))

        conn.commit()
        order_id = cursor.lastrowid
        conn.close()

        return {'message': 'Order created', 'order_id': order_id}, 201    
