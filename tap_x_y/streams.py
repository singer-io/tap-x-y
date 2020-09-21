# pylint: disable=E1101
import os
from datetime import timedelta

import singer
from singer.utils import strptime_to_utc

LOGGER = singer.get_logger()


class BaseStream:
    def __init__(self, client=None, config=None, catalog=None, state=None):
        self.client = client
        self.config = config
        self.catalog = catalog
        self.state = state

    @staticmethod
    def get_abs_path(path):
        return os.path.join(os.path.dirname(os.path.realpath(__file__)), path)

    def load_schema(self):
        schema_path = self.get_abs_path('schemas')
        return singer.utils.load_json('{}/{}.json'.format(
            schema_path, self.name))

    def write_schema(self):
        schema = self.load_schema()
        return singer.write_schema(stream_name=self.name,
                                   schema=schema,
                                   key_properties=self.key_properties)

    def write_state(self):
        return singer.write_state(self.state)

    def update_bookmark(self, stream, value):
        if 'bookmarks' not in self.state:
            self.state['bookmarks'] = {}
        self.state['bookmarks'][stream] = value
        LOGGER.info('Stream: %s - Write state, bookmark value: %s', stream,
                    value)
        self.write_state()

    # Currently syncing sets the stream currently being delivered in the state.
    # If the integration is interrupted, this state property is used to identify
    #  the starting point to continue from.
    # Reference: https://github.com/singer-io/singer-python/blob/master/singer/bookmarks.py#L41-L46
    def update_currently_syncing(self):
        if (self.name is None) and ('currently_syncing' in self.state):
            del self.state['currently_syncing']
        else:
            singer.set_currently_syncing(self.state, self.name)
        singer.write_state(self.state)

    def get_bookmark(self, stream, default):
        # default only populated on initial sync
        if (self.state is None) or ('bookmarks' not in self.state):
            return default
        return self.state.get('bookmarks', {}).get(stream, default)

    # Returns max key and date time for all replication key data in record
    def max_from_replication_dates(self, record):
        date_times = {
            dt: strptime_to_utc(record[dt])
            for dt in self.key_properties if record[dt] is not None
        }
        max_key = max(date_times)
        return date_times[max_key]

    def get_resources_by_date(self, date):
        filter_param = {
            self.bookmark_field + '.filter.start': int(date.timestamp()) * 1000
        }
        return self.client.get_resources(self.get_endpoint(),
                                         self.config.get('space_uri'),
                                         self.config.get('api_user'),
                                         filter_param)

    def get_resources(self):
        return self.client.get_resources(self.get_endpoint())

    @staticmethod
    def remove_hours_local(dttm):
        new_dttm = dttm.replace(hour=0, minute=0, second=0, microsecond=0)
        return new_dttm

    # Round time based to day
    def round_time(self, start=None):
        start_rounded = None
        # Round min_start, max_end to hours or dates
        start_rounded = self.remove_hours_local(start) - timedelta(days=1)
        return start_rounded

    def sync(self, bookmark):
        return self.get_resources_by_date(bookmark)


class SalesOrderline(BaseStream):
    name = 'sales_order_line'
    key_properties = ['id']
    replication_method = 'INCREMENTAL'
    bookmark_field = 'lastModified'
    valid_replication_keys = ['lastModified']
    endpoint = 'commerce.salesorderline-{sales_order_line}'
    uri_root = 'commerce'
    uri_root_path = 'store'

    def get_endpoint(self):
        return self.endpoint.format(
            sales_order_line=self.config.get('sales_order_line'))


class Customer(BaseStream):
    name = 'customer'
    key_properties = ['id']
    replication_method = 'INCREMENTAL'
    valid_replication_keys = ['lastModified']
    bookmark_field = 'lastModified'
    endpoint = '{customer}'

    def get_endpoint(self):
        return self.endpoint.format(customer=self.config.get('customer'))


class Inventory(BaseStream):
    name = 'inventory'
    key_properties = ['id']
    replication_method = 'INCREMENTAL'
    valid_replication_keys = ['lastModified']
    bookmark_field = 'lastModified'
    endpoint = 'commerce.inventory-{inventory}'

    def get_endpoint(self):
        return self.endpoint.format(inventory=self.config.get('inventory'))


class Invoice(BaseStream):
    name = 'invoice'
    key_properties = ['id']
    key_properties = ['id']
    replication_method = 'INCREMENTAL'
    valid_replication_keys = ['lastModified']
    bookmark_field = 'lastModified'
    endpoint = '{invoice}'

    def get_endpoint(self):
        return self.endpoint.format(invoice=self.config.get('invoice'))


class InventoryMovement(BaseStream):
    name = 'inventory_movement'
    key_properties = ['id']
    replication_method = 'INCREMENTAL'
    valid_replication_keys = ['lastModified']
    bookmark_field = 'lastModified'
    endpoint = '{inventory_movement}'

    def get_endpoint(self):
        return self.endpoint.format(
            inventory_movement=self.config.get('inventory_movement'))


class Item(BaseStream):
    name = 'item'
    key_properties = ['id']
    replication_method = 'INCREMENTAL'
    valid_replication_keys = ['lastModified']
    bookmark_field = 'lastModified'
    endpoint = 'commerce.item-{item}'

    def get_endpoint(self):
        return self.endpoint.format(item=self.config.get('item'))


class StockTransfer(BaseStream):
    name = 'stock_transfer'
    key_properties = ['id']
    replication_method = 'INCREMENTAL'
    valid_replication_keys = ['lastModified']
    bookmark_field = 'lastModified'
    endpoint = 'commerce.stocktransferline-{stock_transfer}'

    def get_endpoint(self):
        return self.endpoint.format(
            stock_transfer=self.config.get('stock_transfer'))


AVAILABLE_STREAMS = {
    "sales_order_line": SalesOrderline,
    "customer": Customer,
    "inventory": Inventory,
    "invoice": Invoice,
    "inventory_movement": InventoryMovement,
    "item": Item,
    "stock_transfer": StockTransfer
}
