import dash
from dash import callback, html, dcc
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
from utils.agg_utils import calculate_block_holes
from ui.components import create_data_table, create_dropdown, create_date_range_picker
from db.assignments.db_support import fetch_managers, fetch_centers, fetch_date_range, fetch_vehicle_shifts, create_vehicle_shifts
import plotly.express as px
from datetime import datetime

dash.register_page(__name__, path='/assignments')

import warnings
warnings.filterwarnings("ignore", message="Mean of empty slice")

import pandas as pd

layout = html.Div([
    dcc.Tabs(id='tabs', value='historical', children=[
        dcc.Tab(label='Historical', value='historical'),
        dcc.Tab(label='Realtime', value='realtime')
    ], className="col-md-3 offset-md-1 col-12"),
    html.Div(id='assignment-tabs-content')
])

@callback(
    Output('assignment-tabs-content', 'children'),
    Input('tabs', 'value')
)
def render_content(tab):
    if tab == 'realtime':
        return [
            dbc.Container([
                dbc.Row([
                    dbc.Col([
                        html.Div(id='realtime-block-holes-container', children=[]),
                        html.Button('Download CSV', id='download-rt-block-holes-csv', n_clicks=0)
                        ])
                        ])
                        ])
        ]
    else:
        manager_options = fetch_managers().to_dict('records')
        center_options = fetch_centers().to_dict('records')
        min_date, max_date = fetch_date_range()
        return [
            dbc.Container([
                dbc.Row([
                    dbc.Col([
                        create_dropdown('manager-dropdown', options=manager_options, label='name', value='name', placeholder='Select manager', multi=False, add_all=True),
                        create_date_range_picker('date-picker-range', min_date, max_date),
                        html.Div(id='hist-block-holes-grid-graph-container', children=[]),
                        html.Button('Download CSV', id='download-block-holes-csv', n_clicks=0)
                    ])
                    ])
                    ])
                    ]

@callback(
    Output('hist-block-holes-grid-graph-container', 'children'),
    Input('tabs', 'value'),
    Input('manager-dropdown', 'value'),
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date')
)
def update_historical_block_holes_container(tab, selected_manager, start_date, end_date):
    if tab != 'historical':
        return dash.no_update
    
    if not selected_manager:
        return dash.no_update
    
    vehicle_shifts_hist = fetch_vehicle_shifts(from_date=start_date, to_date=end_date)
    block_holes = calculate_block_holes(vehicle_shifts_hist)
    
    if selected_manager == 'all':
        block_holes = block_holes.drop(columns=['manager', 'center'])
        block_holes = block_holes.groupby(['date']).sum().reset_index()
        wide_df = pd.melt(block_holes, id_vars=['date'], var_name='shift', value_name='holes')
        pivot_df = wide_df.pivot(index='shift', columns='date', values='holes').reset_index()
           
    if selected_manager != 'all':
        block_holes = block_holes[block_holes['manager'] == selected_manager]
        block_holes = block_holes.drop(columns=['manager', 'center'])
        wide_df = pd.melt(block_holes, id_vars=['date'], var_name='shift', value_name='holes')
        wide_df = wide_df.groupby(['date', 'shift']).sum().reset_index()
        pivot_df = wide_df.pivot(index='shift', columns='date', values='holes').reset_index()

    fig = px.line(wide_df, x='date', y='holes', color='shift', title='Unassigned Spots Over Time')
    fig.update_xaxes(rangeslider_visible=True)
    fig.update_xaxes(
        tickmode='array',
        tickvals=wide_df['date'].unique(),
        ticktext=wide_df['date'],
        tickangle=-45
    )
    grid = create_data_table('block-holes-grid', pivot_df, 'block_holes.csv', len(block_holes), custom_height='300px')
    return [dcc.Graph(figure=fig), grid]


@callback(
    Output('realtime-block-holes-container', 'children'),
    Input('tabs', 'value')
)
def update_data_table(tab):
    if tab == 'realtime':
        vehicle_shifts_general = create_vehicle_shifts()
        
        general_block_holes = calculate_block_holes(vehicle_shifts_general)
        today = datetime.today().strftime('%Y-%m-%d')
        general_block_holes_grid = create_data_table('block-holes-grid', general_block_holes, f'block_holes_{today}.csv', len(general_block_holes) ,custom_height='1000px')
        
        return general_block_holes_grid
    else:
        return dash.no_update

@callback(
        Output('block-holes-grid', 'exportDataAsCsv'),
        Input('download-block-holes-csv', 'n_clicks')
        )
def download_csv(n_clicks):
    if n_clicks > 0:
        return True
    return dash.no_update
