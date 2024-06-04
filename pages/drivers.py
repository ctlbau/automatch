import dash
from dash import callback, html, dcc
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
from db.drivers import fetch_drivers_exchange_location_and_shift, fetch_provinces, fetch_driver_events_for_weeks, get_min_max_dates_from_schedule_events, fetch_managers, fetch_plates
from ui.components import create_data_table, create_modal, create_dropdown, create_date_range_picker
from utils.agg_utils import process_vacation_availability
from datetime import datetime
import plotly.express as px

dash.register_page(__name__, path='/drivers')

layout = html.Div([
    dcc.Tabs(id='driver-tabs', value='availability', children=[
        dcc.Tab(label='Vacations', value='availability'),
        dcc.Tab(label='Exchange Locations', value='exchange-locations')
    ], className="col-md-3 offset-md-1 col-12"),
    html.Div(id='driver-tabs-content')
])

@callback(
    Output('driver-tabs-content', 'children'),
    Input('driver-tabs', 'value')
)
def render_content(tab):
    if tab == 'availability':
        min_date, max_date = get_min_max_dates_from_schedule_events()
        manager_options = fetch_managers().to_dict('records')
        plates_options = fetch_plates().to_dict('records')
        vacations_layout = dbc.Container([
            dbc.Row([
                dbc.Col([
                    create_date_range_picker('availability-date-range-picker', min_date, max_date),
                    create_dropdown('manager-dropdown', options=manager_options, label='name', value='name', placeholder='Select manager', multi=False, add_all=True),
                    create_dropdown('plate-dropdown', options=plates_options, label='plate', value='plate', placeholder='Select plate', multi=False, add_all=False),
                    dcc.Loading(html.Div(id='driver-availability-container', children=[], style={'width': '100%'}), type='circle'),
                ])
            ])
        ])
        return vacations_layout
    elif tab == 'exchange-locations':
        exchange_layout = dbc.Container([
            dbc.Row([
                dbc.Col([
                    create_dropdown('province-dropdown', options=fetch_provinces().to_dict('records'), label='name', value='id', placeholder='Select Province', multi=True, add_all=True),
                    html.Div(id='driver-count-per-exchange-location-and-shift-container', children=[]),
                    html.Button('Download CSV', id='download-driver-count-per-exchange-location-and-shift-csv', n_clicks=0),
                    create_modal('driver-count-disaggregation-modal', 'driver-count-disaggregation-title', 'driver-count-disaggregation-content', 'driver-count-disaggregation-footer')
                ])
            ])
        ])
        return exchange_layout

@callback(
    Output('driver-availability-container', 'children'),
    Input('availability-date-range-picker', 'start_date'),
    Input('availability-date-range-picker', 'end_date'),
    Input('manager-dropdown', 'value'),
    Input('plate-dropdown', 'value'),
    prevent_initial_callback=True
)
def create_vacations_grid(start_date, end_date, manager, plate):
    if start_date and end_date and manager:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        start_week, end_week = start_date.isocalendar()[1], end_date.isocalendar()[1]
        availability = fetch_driver_events_for_weeks(start_date.year, start_week, end_date.year, end_week, manager)
        availability = process_vacation_availability(availability)
        if manager:
            availability = availability.drop(columns=['manager'])
        if plate:
            availability = availability[availability['plate'] == plate]
        page_size = len(availability)
        custom_height = '700px' if page_size > 10 else None
        grid = create_data_table("driver-availability-grid", availability, f"driver-availability-for-{start_date}-{end_date}.csv", page_size=page_size, custom_height=custom_height)
        return grid
    else:
        return None

@callback(
    Output('driver-count-per-exchange-location-and-shift-container', 'children'),
    Input('province-dropdown', 'value')
)
def create_data_table_on_page_load(province_ids):
    if province_ids:
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
        State('province-dropdown', 'value')
    ],
    prevent_initial_callback=True
)
def open_modal(clicked_cell, clicked_row, province_ids):
    if (clicked_cell and 'colId' in clicked_cell and 'value' in clicked_cell and
        clicked_row and clicked_row[0] and 'exchange location' in clicked_row[0] and
        clicked_cell['colId'] != 'exchange location' and clicked_cell['colId'] != 'Total' and
        clicked_row[0]['exchange location'] != 'Total' and clicked_cell['value'] > 0):
        
        shift = clicked_cell['colId']
        value = clicked_cell['value']
        exchange_location = clicked_row[0]['exchange location']
        drivers_exchange_location_and_shift = fetch_drivers_exchange_location_and_shift(province_ids)
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