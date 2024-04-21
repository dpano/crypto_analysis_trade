from flask_restful import Resource

from db.database import get_db_cursor


    
class SignalList(Resource):
    def get(self):
        conn = get_db_cursor()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trading_signals")
        orders = cursor.fetchall()
        conn.close()

        # Convert rows to a list of dicts
        orders_list = [dict(order) for order in orders]

        return orders_list
    
       
