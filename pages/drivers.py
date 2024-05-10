import dash
from dash import callback, html, dcc
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
from db.drivers import fetch_driver_count_per_exchange_location_and_shift
from ui.components import create_data_table
from datetime import datetime

dash.register_page(__name__, path='/drivers')

layout = dbc.Container([
    dcc.Location(id='url', refresh=False),
    dbc.Row([
        dbc.Col([
            html.Div(id='driver-count-per-exchange-location-and-shift-container', children=[]),
            html.Button('Download CSV', id='download-driver-count-per-exchange-location-and-shift-csv', n_clicks=0)
        ])
    ])
])

@callback(
    Output('driver-count-per-exchange-location-and-shift-container', 'children'),
    Input('url', 'pathname')
)
def create_data_table_on_page_load(pathname):
    if pathname == '/drivers':
        driver_count_data = fetch_driver_count_per_exchange_location_and_shift()
        driver_count_data_pivot = driver_count_data.pivot(
            index='exchange_location',
            columns='shift',
            values='count'
            ).reset_index()
        driver_count_data_pivot.fillna(0, inplace=True)
        today = datetime.today().strftime('%Y-%m-%d')
        grid =  create_data_table("driver-count-per-exchange-location-and-shift-grid", 
                                 driver_count_data_pivot, 
                                 f"driver-count-per-exchange-location-and-shift-on-{today}.csv",
                                 page_size=10)
        return [grid]
    else:
        return None
    
@callback(
        Output('driver-count-per-exchange-location-and-shift-grid', 'exportDataAsCsv'),
        Input('download-driver-count-per-exchange-location-and-shift-csv', 'n_clicks')
        )
def download_csv(n_clicks):
    if n_clicks > 0:
        return True
    return dash.no_update

