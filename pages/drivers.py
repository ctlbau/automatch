import dash
from dash import callback, html, dcc
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
from db.drivers import fetch_drivers_exchange_location_and_shift, fetch_provinces
from ui.components import create_data_table, create_modal, create_dropdown
from datetime import datetime
import plotly.express as px

dash.register_page(__name__, path='/drivers')

layout = dbc.Container([
    dcc.Location(id='url', refresh=False),
    dbc.Row([
        dbc.Col([
            create_dropdown('province-dropdown', options=fetch_provinces().to_dict('records'), label='name', value='id', placeholder='Select Province', multi=True, add_all=True),
            html.Div(id='driver-count-per-exchange-location-and-shift-container', children=[]),
            html.Button('Download CSV', id='download-driver-count-per-exchange-location-and-shift-csv', n_clicks=0),
            create_modal('driver-count-disaggregation-modal', 'driver-count-disaggregation-title', 'driver-count-disaggregation-content', 'driver-count-disaggregation-footer')
        ])
    ])
])

@callback(
    Output('driver-count-per-exchange-location-and-shift-container', 'children'),
    Input('province-dropdown', 'value')
)
def create_data_table_on_page_load(province_ids):
    if province_ids:
        print(province_ids)
        if 'all' in province_ids:
            province_ids = fetch_provinces()['id'].tolist()
        drivers_exchange_location_and_shift = fetch_drivers_exchange_location_and_shift(province_ids)
        drivers_exchange_location_and_shift['exchange_location'] = drivers_exchange_location_and_shift['exchange_location'].fillna('Unknown')
        driver_count_data = drivers_exchange_location_and_shift.groupby(['exchange_location', 'shift']).size().reset_index(name='count')
        driver_count_data_pivot = driver_count_data.pivot(
            index='exchange_location',
            columns='shift',
            values='count'
            )
        driver_count_data_pivot.fillna(0, inplace=True)
        driver_count_data_melted = driver_count_data_pivot.reset_index().melt(id_vars='exchange_location', var_name='shift', value_name='count')
        
        fig = px.bar(driver_count_data_melted, x='exchange_location', y='count', color='shift', barmode='group',
                 title='Driver Count per Exchange Location and Shift')
        fig.update_layout(
            xaxis_title='Exchange Location',
            yaxis_title='Count',
            legend_title='Shift'
            )
        
        driver_count_data_pivot.loc[:, 'Total'] = driver_count_data_pivot.sum(axis=1)
        driver_count_data_pivot.loc['Total', :] = driver_count_data_pivot.sum(axis=0)
        driver_count_data_pivot.reset_index(inplace=True)
        today = datetime.today().strftime('%Y-%m-%d')
        grid =  create_data_table("driver-count-per-exchange-location-and-shift-grid", 
                                 driver_count_data_pivot, 
                                 f"driver-count-per-exchange-location-and-shift-on-{today}.csv",
                                 page_size=10)
        return [dcc.Graph(figure=fig), grid]
    else:
        return None

@callback(
    Output('driver-count-disaggregation-modal', 'is_open'),
    Output('driver-count-disaggregation-title', 'children'),
    Output('driver-count-disaggregation-content', 'children'),
    [
        Input('driver-count-per-exchange-location-and-shift-grid', 'cellClicked'),
        Input('driver-count-per-exchange-location-and-shift-grid', 'selectedRows'),
    ],
    prevent_initial_callback=True
)
def open_modal(clicked_cell, clicked_row):
    if (clicked_cell and 'colId' in clicked_cell and 'value' in clicked_cell and
        clicked_row and clicked_row[0] and 'exchange location' in clicked_row[0] and
        clicked_cell['colId'] != 'exchange location' and clicked_cell['colId'] != 'Total' and
        clicked_row[0]['exchange location'] != 'Total' and clicked_cell['value'] > 0):
        
        shift = clicked_cell['colId']
        value = clicked_cell['value']
        exchange_location = clicked_row[0]['exchange location']
        drivers_exchange_location_and_shift = fetch_drivers_exchange_location_and_shift()
        drivers_exchange_location_and_shift['exchange_location'] = drivers_exchange_location_and_shift['exchange_location'].fillna('Unknown')
        drivers_exchange_location_and_shift_filtered = drivers_exchange_location_and_shift[
            (drivers_exchange_location_and_shift['exchange_location'] == exchange_location) &
            (drivers_exchange_location_and_shift['shift'] == shift)
        ]
        grid = create_data_table("driver-count-disaggregation-grid", drivers_exchange_location_and_shift_filtered, f"driver-count-disaggregation-for-{exchange_location}-{shift}.csv")
        return True, f"Found {value} drivers for {exchange_location} with shift {shift}", grid
    else:
        return False, None, None

@callback(
        Output('driver-count-per-exchange-location-and-shift-grid', 'exportDataAsCsv'),
        Input('download-driver-count-per-exchange-location-and-shift-csv', 'n_clicks')
        )
def download_csv(n_clicks):
    if n_clicks > 0:
        return True
    return dash.no_update