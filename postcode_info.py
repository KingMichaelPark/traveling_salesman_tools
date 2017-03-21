# Tools for Dealing with Postcodes
import pandas as pd
import sqlalchemy as sql
from numpy import nan
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
import requests


def define_engine(conn):
    return sql.create_engine(conn)


def prepare_base(engine):
    Base = automap_base()
    Base.prepare(engine, reflect=True)
    return Base


def get_session(engine):
    Session = sessionmaker()
    return Session()


def get_lat(x, session, table_object):
    try:
        return session.query(table_object.latitude).filter(
            table_object.postcode == x).first()[0]
    except Exception as e:
        print(e)
        return nan


def get_lon(x, session, table_object):
    try:
        return session.query(table_object.longitude).filter(
            table_object.postcode == x).first()[0]
    except Exception as e:
        print(e)
        return nan


class PostcodeIO:
    def __init__(self, url):
        self.url = url

    def add_postcodes(self, list_of_pcodes):
        self.postcodes = list_of_pcodes
        r = requests.post(
            self.url,
            data={"postcodes": list_of_pcodes}
        )
        return r.json()

