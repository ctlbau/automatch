import os
import dash
import dash_deck as dd
from dash_deck import DeckGL
import pydeck as pdk
from dash import html, dcc, callback, MATCH
from utils.geo_utils import geoencode_address, calculate_isochrones, partition_drivers_by_isochrones, extract_coords_from_encompassing_isochrone, check_partitions_intersection, calculate_driver_distances_and_paths
from utils.agg_utils import get_manager_distance_stats
from db.automatch import fetch_drivers, fetch_shifts, fetch_managers, fetch_centers, fetch_provinces, fetch_exchange_locations
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
from dash.dependencies import ALL
from ui.components import create_data_table, create_dropdown, create_map_container, create_modal, plot_distance_histogram, create_modal
from datetime import datetime
import pandas as pd

dash.register_page(__name__, path='/')

MAPBOX_API_KEY = os.getenv("MAPBOX_TOKEN")
ATOCHA = (-3.690633, 40.406785)
MAP_STYLES = ["mapbox://styles/mapbox/light-v9", "mapbox://styles/mapbox/dark-v9", "mapbox://styles/mapbox/satellite-v9"]
CHOSEN_STYLE = MAP_STYLES[0]

iso_tooltip={
    "html": """<b>Name:</b> {name}<br>
               <b>Street:</b> {street}<br>
               <b>Manager:</b> {manager}<br>
               <b>Shift:</b> {shift} <br> 
               <b>Center:</b> {center} <br> 
               <b>Matched:</b> {is_matched} <br> 
               <b>Matched With:</b> {matched_with} <br>
               <b>Exchange Location:</b> {exchange_location}""",
    "style": {
        "backgroundColor": "steelblue",
        "color": "white"
        }
        }

iso_layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dcc.Input(id='street-input', type='text', placeholder='Enter street name and number', required=True, className='form-control mb-2', autoFocus=True),
                            create_dropdown('province-dropdown', options=fetch_provinces().to_dict('records'), label='name', value='id', placeholder='Select a province', multi=False, class_name='mb-2'),
                            dcc.Input(id='zip-code-input', type='text', placeholder='Enter zip code', name='Zip code', required=False, className='form-control mb-2'),
                            html.Label([
                                'Isochrone Limits:',
                                html.Br(),
                                html.Span('(in minutes)', style={'fontSize': '0.8em', 'color': '#6c757d'})
                            ], className='me-2 my-auto'),
                            dcc.RangeSlider(
                                id='time-limit-range-slider',
                                min=5, max=60, step=5, value=[5, 10],
                                marks={i: f'{i}' for i in range(5, 61, 5)},
                                className='mb-3'
                            ),
                            create_dropdown('shifts-dropdown', options=fetch_shifts().to_dict('records'), label='name', value='name', placeholder='Select a shift', multi=True, class_name='mb-3'),
                            create_dropdown('managers-dropdown', options=fetch_managers().to_dict('records'), label='name', value='name', placeholder='Select a manager', multi=True, class_name='mb-3'),
                            create_dropdown('center-dropdown', options=fetch_centers().to_dict('records'), label='name', value='name', placeholder='Select a center', multi=True, class_name='mb-3'),
                            create_dropdown('exchange-locations-dropdown', options=fetch_exchange_locations().to_dict('records'), label='name', value='name', placeholder='Select an exchange location', multi=True, class_name='mb-3'),
                            dbc.Row([
                                dbc.Col(html.Label('Filter by Match Status:', className='mr-2'), width='auto'),
                                dbc.Col(dcc.RadioItems(
                                    id='is-matched-radio',
                                    options=[
                                        {'label': 'All', 'value': 'all'},
                                        {'label': 'True', 'value': 'true'},
                                        {'label': 'False', 'value': 'false'},
                                    ],
                                    value='all',
                                    inline=True,
                                ), width='auto'),
                                dbc.Col(dbc.Button('Submit', id='submit-val', n_clicks=0, color="primary"), width='auto'),
                            ], className='align-items-center mb-2'),
                        ], width=12, lg=3),
                        dbc.Col(
                            dbc.Card([
                                dbc.CardBody(
                                    html.Div(
                                        create_map_container('isomatch-map', initial_view_coords=ATOCHA, tooltip_info=iso_tooltip, map_style=CHOSEN_STYLE), 
                                        style={'height': '500px', 'width': '100%'},
                                        className='map-wrapper'
                                    )
                                )
                            ], className='mb-3'),
                            width=12, lg=9
                        ),
                    ]),
                ], className='px-2 py-2'),
            ], className='mb-3'),
            
            dbc.Alert(
                id="alert-fail-geoencode",
                children="Unable to find location. Please check the address and zip code, then try again.",
                color="danger",
                dismissable=True,
                is_open=False,
                className='mb-3',
            ),
            html.Div(id='data-tables-container', children=[]),
        ], width=12, lg=11, xl=11, className='px-3'),
    ], justify='start', className='mx-0'),
], fluid=True, className='mt-3 px-1')

stats_layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            dcc.Store(id='error-data-store'),
            create_modal("error-modal", "error-modal-title", "error-details-grid", "error-modal-footer"),
            create_modal('manager-stats-modal', 'manager-stats-modal-title', 'manager-stats-modal-body', 'manager-stats-modal-footer'),
            
            dbc.Card([
                dbc.CardBody(
                    dcc.Loading(
                        id="loading-peak-container",
                        type="circle",
                        children=[
                            dbc.Row([
                                dbc.Col(create_dropdown(
                                    id='exchange-locations-dropdown',
                                    options=fetch_exchange_locations().to_dict('records'),
                                    label='name',
                                    value='name',
                                    placeholder='Select an exchange location',
                                    multi=False,
                                    add_all=True,
                                    class_name="mb-3"
                                ), width=12, lg=4),
                            ], justify="start"),
                            dbc.Row([
                                dbc.Col(
                                    html.Div(id='stats-graph-container', style={'height': '500px', 'width': '100%'}, className='map-wrapper'),
                                    width=12
                                ),
                            ], justify="start"),
                        ]
                    )
                ),
            ], className='mb-3'),
            
            html.Div(id='stats-grid-container', children=[], className='mb-3'),
            dbc.Collapse(
                dbc.Row([
                    dbc.Col([
                        dbc.Button("Show Errors", id="show-error-modal-btn", color="secondary", className="me-2"),
                        dbc.Button("Download CSV", id="download-manager-stats-csv-btn", color="primary"),
                    ], width="auto"),
                ], justify="center", className='mt-3'),
                id="button-collapse",
                is_open=False,
            ),
        ], width=12, lg=11, xl=11, className='px-3'),
    ], justify='center', className='mx-0'),
], fluid=True, className='mt-3 px-1')

@callback(
    Output("content", "className"),
    Input("sidebar-state", "data")
)
def adjust_content(sidebar_state):
    if sidebar_state == "closed":
        return "mt-3 px-3 content-expanded"
    return "mt-3 px-3"

layout = dbc.Container([
    dbc.Tabs(id="tabs", active_tab='iso-tab', children=[
        dbc.Tab(label='Isomatch', tab_id='iso-tab'),
        dbc.Tab(label='Matchstats', tab_id='stats-tab'),
    ], className="nav-fill w-100 mb-3"),
    html.Div(id='isomatch-tabs-content', style={'height': 'calc(100vh - 100px)'})
], fluid=True, className='mt-3 px-3', id='content')

@callback(
    Output('isomatch-tabs-content', 'children'),
    Input('tabs', 'active_tab')
)
def render_content(tab):
    if tab == 'iso-tab':
        return iso_layout
    elif tab == 'stats-tab':
        return stats_layout
    else:
        return None

@callback(
    Output('stats-graph-container', 'children'), 
    Output('stats-grid-container', 'children'), 
    Output('error-data-store', 'data'),
    Output('button-collapse', 'is_open'),
    Input('exchange-locations-dropdown', 'value'),
    State('sidebar-state', 'data'),
    State('exchange-locations-dropdown', 'options'),
)
def update_stats_grid_and_graph(exchange_locations_id, sidebar_state, exchange_locations_options):
    if exchange_locations_id is not None:
        today = datetime.now().strftime("%Y-%m-%d")  
        if exchange_locations_id == 0:  # All exchange locations selected
            drivers_gdf, _ = fetch_drivers([28, 46, 8, 41, 29])  
            drivers_gdf_w_paths_and_distances, error_df = calculate_driver_distances_and_paths(drivers_gdf)
            drivers_gdf_w_paths_and_distances = drivers_gdf_w_paths_and_distances.dropna(subset=['distance'])
            fig = plot_distance_histogram(drivers_gdf_w_paths_and_distances)
            manager_stats = get_manager_distance_stats(drivers_gdf_w_paths_and_distances, "All")
            grid = create_data_table('manager-stats', manager_stats, f'manager_stats_{today}.csv', page_size=20, custom_height='800px')
        else:
            # Specific exchange location selected
            selected_option = next((option for option in exchange_locations_options if option['value'] == exchange_locations_id), None)
            if selected_option:
                exchange_location = selected_option['label']
                drivers_gdf, _ = fetch_drivers([28, 46, 8, 41, 29])
                drivers_gdf_w_paths_and_distances, error_df = calculate_driver_distances_and_paths(drivers_gdf)
                drivers_gdf_w_paths_and_distances = drivers_gdf_w_paths_and_distances.dropna(subset=['distance'])
                fig = plot_distance_histogram(drivers_gdf_w_paths_and_distances)
                manager_stats = get_manager_distance_stats(drivers_gdf_w_paths_and_distances, exchange_location)
                manager_stats = manager_stats.drop(columns=['exchange_location'])
                grid = create_data_table('manager-stats', manager_stats, f'manager_stats_{today}_at_{exchange_location}.csv', page_size=20, custom_height='800px')
            else:
                return dash.no_update, dash.no_update, dash.no_update, False

        return [
            fig,
            grid,
            error_df.to_dict('records') if error_df is not None else None,
            True
        ]
    return dash.no_update, dash.no_update, dash.no_update, False  # Hide the buttons

@callback(
    Output('manager-stats-modal', 'is_open'),
    Output('manager-stats-modal-title', 'children'),
    Output('manager-stats-modal-body', 'children'),
    Input('manager-stats', 'cellClicked'),
    State('exchange-locations-dropdown', 'options'),
    State('exchange-locations-dropdown', 'value')
)
def display_manager_details(cell, exchange_locations_options, exchange_locations_id):
    if cell and cell['colId'] == 'manager':
        manager = cell['value']
        drivers_gdf, _ = fetch_drivers([28, 46, 8, 41, 29])
        drivers_gdf = drivers_gdf[drivers_gdf['manager'] == manager]
        selected_option = next((option for option in exchange_locations_options if option['value'] == exchange_locations_id), None)
        if selected_option is not None:
            exchange_location = selected_option['label']
            if exchange_location != 'All':
                drivers_gdf = drivers_gdf[drivers_gdf['exchange_location'] == exchange_location]
        drivers_gdf_w_paths_and_distances, _ = calculate_driver_distances_and_paths(drivers_gdf)
        drivers_gdf_w_paths_and_distances = drivers_gdf_w_paths_and_distances.dropna(subset=['distance'])
        fig = plot_distance_histogram(drivers_gdf_w_paths_and_distances)
        drivers_gdf_w_paths_and_distances = drivers_gdf_w_paths_and_distances.drop(columns=['geometry', 'path', 'province', 'lat', 'lng', 'driver_id', 'manager'])
        grid = create_data_table(f'manager-stats-modal-{manager}', drivers_gdf_w_paths_and_distances, f'manager_stats_{manager}.csv', page_size=20)
        today = datetime.now().strftime("%Y-%m-%d")
        title = f"{manager} on {today}"
        
        if grid is not None and fig is not None:
            return True, title, [fig, grid]
        else:
            return False, dash.no_update, dash.no_update
    return False, dash.no_update, dash.no_update


@callback(
        Output('manager-stats', 'exportDataAsCsv'),
        Input('download-manager-stats-csv-btn', 'n_clicks'),
        prevent_initial_call=True
)
def download_manager_stats_csv(n_clicks):
    if n_clicks > 0:
        return True
    return dash.no_update

@callback(
    Output("show-error-modal-btn", "style"),
    Input("error-data-store", "data"),
)
def toggle_error_button_visibility(error_data):
    if error_data:
        return {"display": "block"}
    else:
        return {"display": "none"}

@callback(
    Output("error-modal", "is_open"),
    Output("error-details-grid", "children"),
    Input("show-error-modal-btn", "n_clicks"),
    State("error-data-store", "data"),
    prevent_initial_call=True
)
def update_error_modal(n_clicks, error_data):
    if n_clicks > 0 and error_data:
        error_df = pd.DataFrame(error_data)
        if not error_df.empty:
            error_table = create_data_table('Error Details', error_df, 'error_details.csv', page_size=10)
            return True, error_table
    return False, []

@callback(
    [
        Output('isomatch-map', 'data'), 
        Output('data-tables-container', 'children'),
        Output('alert-fail-geoencode', 'is_open')
        ],
    [
        Input('submit-val', 'n_clicks'), 
        Input('shifts-dropdown', 'value'), 
        Input('managers-dropdown', 'value'),
        Input('is-matched-radio', 'value'), 
        Input('center-dropdown', 'value'), 
        Input('exchange-locations-dropdown', 'value')
        ],
    [
        State('street-input', 'value'),
        State('province-dropdown', 'options'),
        State('province-dropdown', 'value'),
        State('zip-code-input', 'value'),
        State('time-limit-range-slider', 'value')
        ]
)
def update_map_and_tables(n_clicks, selected_shifts, selected_managers, is_matched_filter, selected_center, exchange_locations, street, selected_province, province_id, postal_code, time_limits):
    if n_clicks > 0:
        province = [province for province in selected_province if province['value'] == province_id][0]['label']
        geoencode_result = geoencode_address(street, province, postal_code)

        if geoencode_result is None:
            return dash.no_update, dash.no_update, True
        
        if geoencode_result:
            lat, lon = geoencode_result
            lat, lon = float(lat), float(lon)
            times = list(range(time_limits[0], time_limits[1] + 1, 5))
            isochrones_geojson = calculate_isochrones(lat, lon, times)
            isochrone_coords = extract_coords_from_encompassing_isochrone(isochrones_geojson)
            computed_view_state = pdk.data_utils.compute_view(isochrone_coords, view_proportion=0.9)
            drivers_gdf, drivers_list = fetch_drivers([province_id])
            
            if selected_shifts:
                drivers_list = [driver for driver in drivers_list if driver['shift'] in selected_shifts]
                drivers_gdf = drivers_gdf[drivers_gdf['shift'].isin(selected_shifts)]
            
            if selected_managers:
                drivers_list = [driver for driver in drivers_list if driver['manager'] in selected_managers]
                drivers_gdf = drivers_gdf[drivers_gdf['manager'].isin(selected_managers)]

            if is_matched_filter != 'all':
                is_matched_value = True if is_matched_filter == 'true' else False
                drivers_list = [driver for driver in drivers_list if driver['is_matched'] == is_matched_value]
                drivers_gdf = drivers_gdf[drivers_gdf['is_matched'] == is_matched_value]
            
            if selected_center:
                drivers_list = [driver for driver in drivers_list if driver['center'] in selected_center]
                drivers_gdf = drivers_gdf[drivers_gdf['center'].isin(selected_center)]
            
            if exchange_locations:
                drivers_list = [driver for driver in drivers_list if driver['exchange_location'] in exchange_locations]
                drivers_gdf = drivers_gdf[drivers_gdf['exchange_location'].isin(exchange_locations)]

            icon_data = {
                "url": "https://upload.wikimedia.org/wikipedia/commons/3/3b/Blackicon.png",
                "width": 100,
                "height": 100,
                # "anchorY": 242,
            }

            # Create an IconLayer for the geoencoded point
            icon_layer = pdk.Layer(
                "IconLayer",
                data=[{"coordinates": [lon, lat], "icon_data": icon_data}],
                get_icon="icon_data",
                get_size=4,
                size_scale=15,
                get_position="coordinates",
                pickable=True,
            )

            isochrone_layer = pdk.Layer(
                "GeoJsonLayer",
                data=isochrones_geojson,
                opacity=0.1,
                stroked=False,
                filled=True,
                extruded=False,
                wireframe=True
            )

            drivers_layer = pdk.Layer(
                "ScatterplotLayer",
                data=drivers_list,
                get_position="coordinates",
                get_color="color",
                get_radius="radius",
                pickable=True,
                auto_highlight=True,
            )
            initial_view_state = computed_view_state

            new_deck_data = pdk.Deck(
                layers=[isochrone_layer, drivers_layer, icon_layer],
                initial_view_state=initial_view_state,
                map_style=CHOSEN_STYLE
            ).to_json()

            partitioned_drivers = partition_drivers_by_isochrones(drivers_gdf, isochrones_geojson)
            # assert check_partitions_intersection(partitioned_drivers), "Partitions are not disjoint!"
            
            data_tables = []
            num_partitions = len(partitioned_drivers)
            for i, partition in enumerate(partitioned_drivers):
                partition = partition.drop(columns=['driver_id', 'matched_driver_id', 'geometry', 'lat', 'lng'])
                current_date = datetime.now().strftime("%Y-%m-%d")
                csv_filename = f"drivers_within_{time_limits[0] + i * 5}_min_isochrone_centered_on_{street}_{province}_at_{current_date}.csv"
                table = create_data_table({'type': 'drivers-table', 'index': i}, partition, csv_filename, page_size=10)
                download_button = html.Button('Download CSV', id={'type': 'download-csv', 'index': i}, n_clicks=0)
                if i < num_partitions - 1:
                    number_of_drivers = len(partition)
                    iso_title = time_limits[0] + i * 5 
                    title = f'{number_of_drivers} drivers within {iso_title} minutes of chosen location'
                else:
                    # This is the last partition, so we give it a custom title
                    number_of_drivers = len(partition)
                    title = f'{number_of_drivers} drivers outside largest isochrone'
                data_tables.append(html.Div(children=[html.H3(title), table, download_button], style={'margin': '20px'}))

            return new_deck_data, data_tables, False
        else:
            # No clicks yet, do not update anything and ensure the alert is closed
            return dash.no_update, dash.no_update, False
    return dash.no_update, dash.no_update, False

@callback(
    Output({'type': 'drivers-table', 'index': MATCH}, 'exportDataAsCsv'),
    Input({'type': 'download-csv', 'index': MATCH}, 'n_clicks'),
    prevent_initial_call=True
)
def download_csv(n_clicks):
    if n_clicks > 0:
        return True
    return dash.no_update

@callback(
    Output('isomatch-map', 'style'),
    Input('tabs', 'active_tab')
)
def resize_map(active_tab):
    if active_tab == 'iso-tab':
        return {'width': '100%', 'height': '100%'}
    return {'width': '100%', 'height': '0'}  # Hide map on other tabs
 