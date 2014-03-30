# -*- coding: utf-8 -*-
"""
Created on Mon Mar 24 21:31:41 2014

@author: Goutham
"""

try:
    import sqlalchemy as sql
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

try:
    import psycopg2
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False
    
try :
    import _mysql
    HAS_MYSQL = True
except ImportError:
    HAS_MYSQL = False

import datetime
import unittest
from flask import Blueprint
from . import FlaskTrackUsageTestCase
from flask_track_usage import TrackUsage
from flask_track_usage.storage.sql import SQLStorage
    
@unittest.skipUnless(HAS_SQLALCHEMY, "Requires SQLAlchemy")
class TestSQLiteStorage(FlaskTrackUsageTestCase):

    def _create_storage(self):
        self.storage = SQLStorage(
            conn_str="sqlite://",
            table_name=self.given_table_name
        )
        
    def tearDown(self):
        d = sql.delete(self.storage.track_table,self.storage.track_table.c.id>0)
        con = self.storage._get_connection()
        con.execute(d)
        self.storage._close_connection(con)
    
    def setUp(self):
        self.given_table_name = 'my_usage'
        FlaskTrackUsageTestCase.setUp(self)
        self.blueprint = Blueprint('blueprint', __name__)
        @self.blueprint.route('/blueprint')
        def blueprint():
            return "blueprint"
        self.app.register_blueprint(self.blueprint)
        
        self._create_storage()
    
        self.track_usage = TrackUsage(self.app, self.storage)
        self.track_usage.include_blueprint(self.blueprint)
        
    def test_table_name(self):
       
        meta = sql.MetaData()
        meta.reflect(bind=self.storage._eng)
        assert self.given_table_name == meta.tables.keys()[0]

    def test_storage_data_basic(self):
        self.client.get('/')
        con = self.storage._eng.connect()
        s = sql.select([self.storage.track_table])
        result = con.execute(s).fetchone()
        assert result[0] == 1 # first row
        assert result[1] == u'http://localhost/'
        assert result[2] is None
        assert result[3] is None
        assert result[4] is None
        assert result[5] is None
        assert result[6] is None
        assert result[8] == 200
        assert result[9] is None
        assert result[10] == False
        assert result[11] is None
        assert result[12] == '/'
        assert result[13].__class__ is float
        assert type(result[14]) is datetime.datetime
        
    def test_storage_data_blueprint(self):
        self.client.get('/blueprint')
        con = self.storage._eng.connect()
        s = sql.select([self.storage.track_table])
        result = con.execute(s).fetchone()
        print result
        #assert result[0] == 1 # first row
        assert result[1] == u'http://localhost/blueprint'
        assert result[2] is None
        assert result[3] is None
        assert result[4] is None
        assert result[5] is None
        assert result[6] == 'blueprint'
        assert result[8] == 200
        assert result[9] is None
        assert result[10] == False
        assert result[11] is None
        assert result[12] == '/blueprint'
        assert result[13].__class__ is float
        assert type(result[14]) is datetime.datetime
        
    def test_storage_get_usage(self):
        # First check no blueprint case get_usage is correct
        self.client.get('/')
        result = self.storage._get_usage()[0]
        #assert result[0] == 1 # first row
        assert result[1] == u'http://localhost/'
        assert result[2] is None
        assert result[3] is None
        assert result[4] is None
        assert result[5] is None
        assert result[6] is None
        assert result[8] == 200
        assert result[9] is None
        assert result[10] == False
        assert result[11] is None
        assert result[12] == '/'
        assert result[13].__class__ is float
        assert type(result[14]) is datetime.datetime
        
        # Next check with blueprint the get_usage is correct
        self.client.get('/blueprint')
        rows = self.storage._get_usage()
        result = rows[1] if rows[0][6] is None else rows[0]
        #assert result[0] == 2 # first row
        assert result[1] == u'http://localhost/blueprint'
        assert result[2] is None
        assert result[3] is None
        assert result[4] is None
        assert result[5] is None
        assert result[6] == 'blueprint'
        assert result[8] == 200
        assert result[9] is None
        assert result[10] == False
        assert result[11] is None
        assert result[12] == '/blueprint'
        assert result[13].__class__ is float
        assert type(result[14]) is datetime.datetime
        
        # third get
        self.client.get('/')

        # Limit tests
        assert len(self.storage._get_usage()) == 3
        assert len(self.storage._get_usage(limit=2)) == 2
        assert len(self.storage._get_usage(limit=1)) == 1
        
        # timing tests
        # give a 5 second lag since datetime stored is second precision
        
        now = datetime.datetime.utcnow()+datetime.timedelta(0,5)
        assert len(self.storage._get_usage(start_date=now)) == 0
        assert len(self.storage._get_usage(end_date=now)) == 3
        assert len(self.storage._get_usage(end_date=now, limit=2)) == 2
        
        # test pagination        
        for i in range(100):
            self.client.get('/')
        
        limit = 10
        num_pages = 10
        for page in range(1,num_pages + 1):
            result = self.storage._get_usage(limit=limit,page=page)
            assert len(result) == limit
        
        # actual api test
        result = self.storage._get_usage(limit=100)  # raw data
        result2 = self.storage.get_usage(limit=100)  # dict data
        for i in range(100):
            assert result[i][1] == result2[i]['url']
            assert result[i][2] == result2[i]['user_agent']['browser']
            assert result[i][3] == result2[i]['user_agent']['language']
            assert result[i][4] == result2[i]['user_agent']['platform']
            assert result[i][5] == result2[i]['user_agent']['version']
            assert result[i][6] == result2[i]['blueprint']
            assert result[i][8] == result2[i]['status']
            assert result[i][9] == result2[i]['remote_addr']
            assert result[i][10] == result2[i]['authorization']
            assert result[i][11] == result2[i]['ip_info']
            assert result[i][12] == result2[i]['path']
            assert result[i][13] == result2[i]['speed'] 
            assert result[i][14] == result2[i]['date'] 
        
@unittest.skipUnless(HAS_POSTGRES, "Requires psycopg2 Postgres package")
@unittest.skipUnless((HAS_SQLALCHEMY), "Requires SQLAlchemy")
class TestPostgresStorage(TestSQLiteStorage):    
    
    def _create_storage(self):
        self.storage = SQLStorage(
            conn_str="postgresql+psycopg2://postgres:@localhost/track_usage_test",
            table_name=self.given_table_name
        )
        
@unittest.skipUnless(HAS_MYSQL, "Requires mysql-python package")
@unittest.skipUnless((HAS_SQLALCHEMY), "Requires SQLAlchemy")
class TestMySQLStorage(TestSQLiteStorage):    
    
    def _create_storage(self):
        self.storage = SQLStorage(
            conn_str="mysql+mysqldb://travis:@localhost/track_usage_test",
            table_name=self.given_table_name
        )
