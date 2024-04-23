import dash
from dash import callback, html, dcc
from dash.dependencies import Input, Output
from db.blockbuster import fetch_vehicle_shifts
import dash_bootstrap_components as dbc
import pandas as pd
from utils.agg_utils import calculate_block_holes
from ui.components import create_data_table
from datetime import datetime

dash.register_page(__name__, path='/blockbuster')

layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dbc.Container([
        dbc.Row([
            dbc.Col([
                html.Div(id='block-holes-container', children=[]),
                html.Button('Download CSV', id='download-block-holes-csv', n_clicks=0)
                ])
            ])
        ])
    ])

@callback(
    Output('block-holes-container', 'children'),
    Input('url', 'pathname')
)
def update_data_table(pathname):
    if pathname == '/blockbuster':
        vehicle_shifts_general = fetch_vehicle_shifts()
        # vehicle_shifts_reyes_magos = vehicle_shifts_general[vehicle_shifts_general['exchange_location'] == 'Reyes Magos']
        # vehicle_shifts_urquijo = vehicle_shifts_general[vehicle_shifts_general['exchange_location'] == 'Parking Marqués de Urquijo']
        
        general_block_holes = calculate_block_holes(vehicle_shifts_general)
        # reyes_magos_block_holes = calculate_block_holes(vehicle_shifts_reyes_magos)
        # urquijo_block_holes = calculate_block_holes(vehicle_shifts_urquijo)
        
        # Create the data table component
        today = datetime.today().strftime('%Y-%m-%d')
        general_block_holes_grid = create_data_table('block-holes-grid', general_block_holes, f'block_holes_{today}.csv', 27 ,custom_height='1000px')
        # reyes_magos_block_holes_grid = create_data_table('block-holes-grid', reyes_magos_block_holes, 'reyes_magos_block_holes.csv', 10)
        # urquijo_block_holes_grid = create_data_table('block-holes-grid', urquijo_block_holes, 'urquijo_block_holes.csv', 10)
        
        return general_block_holes_grid
    else:
        return None

@callback(
        Output('block-holes-grid', 'exportDataAsCsv'),
        Input('download-block-holes-csv', 'n_clicks')
        )
def download_csv(n_clicks):
    if n_clicks > 0:
        return True
    return dash.no_update
