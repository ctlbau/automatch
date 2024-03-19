import os
import dash
from dash_deck import DeckGL
from dash import html, callback, ALL
import pydeck as pdk
from utils.geo_utils import geoencode_address, calculate_isochrones, partition_drivers_by_isochrones, extract_coords_from_encompassing_isochrone, check_partitions_intersection
from db.automatch import fetch_drivers, fetch_shifts, fetch_managers, fetch_centers
from dash.dependencies import Input, Output, State
from dash import dcc
from dash import dash_table, dcc, html
import dash_bootstrap_components as dbc
from dash.dependencies import ALL
from ui.components import create_navbar, create_data_table

dash.register_page(__name__, path='/')

BASE_URL = "http://localhost:8989/isochrone"

ATOCHA = (-3.690633, 40.406785)
MAPBOX_API_KEY = os.getenv("MAPBOX_TOKEN")
MAP_STYLES = ["mapbox://styles/mapbox/light-v9", "mapbox://styles/mapbox/dark-v9", "mapbox://styles/mapbox/satellite-v9"]
CHOSEN_STYLE = MAP_STYLES[0]

layout = html.Div([
    # Container for inputs and button
    html.Div([
        dcc.Input(id='street-input', type='text', placeholder='Enter street name and number', required=True, style={'marginRight': '10px', 'width': '350px', 'display': 'block', 'marginBottom': '10px'}),
        html.Div([  # Div to wrap zip-code-input and Submit button
            dcc.Input(id='zip-code-input', type='text', placeholder='Enter zip code', name='Zip code', required=False, style={'marginRight': '10px', 'display': 'inline-block', 'marginBottom': '10px'}),
            html.Button('Submit', id='submit-val', n_clicks=0, style={'display': 'inline-block'}),
        ], style={'display': 'flex', 'flexDirection': 'row'}),
        html.Label('Isochrone Limits (in minutes):', style={'display': 'block', 'marginBottom': '10px'}),
        dcc.RangeSlider(
            id='time-limit-range-slider',
            min=5,
            max=60,
            step=5,
            value=[5, 10],
            marks={i: f'{i}' for i in range(5, 61, 5)},
        ),
        dcc.Dropdown(
            id='shifts-dropdown',
            options=[{'label': shift['name'], 'value': shift['name']} for shift in fetch_shifts().to_dict('records')],
            placeholder='Select a shift',
            multi=True,
            style={'marginBottom': '10px'}
        ),
        dcc.Dropdown(  # Dropdown for managers
            id='managers-dropdown',
            options=[{'label': manager['name'], 'value': manager['name']} for manager in fetch_managers().to_dict('records')],
            placeholder='Select a manager',
            multi=True,
            style={'marginBottom': '10px'}
        ),
        dcc.Dropdown(  # Dropdown for center selection
            id='center-dropdown',
            options=[{'label': center['name'], 'value': center['name']} for center in fetch_centers().to_dict('records')],
            placeholder='Select a center',
            multi=True,
            style={'marginBottom': '10px'}
        ),
        html.Div([  # Div for radio items to display horizontally
            html.Label('Filter by Match Status:', style={'marginRight': '20px', 'marginBottom': '10px'}),
            dcc.RadioItems(  # Radio button for is_matched filter
                id='is-matched-radio',
                options=[
                    {'label': 'All', 'value': 'all'},
                    {'label': 'True', 'value': 'true'},
                    {'label': 'False', 'value': 'false'},
                ],
                value='all',
                labelStyle={'display': 'inline-block', 'marginRight': '20px'},  # Adjusted for horizontal display
                style={'marginBottom': '10px'}
            ),
        ], style={'display': 'flex', 'flexDirection': 'row', 'alignItems': 'center'}),
    ], className="col-md-3 offset-md-0 col-12"),
    
    # Alert for failed geoencoding
    dbc.Alert(
        id="alert-fail-geoencode",
        children="Unable to find location. Please check the address and zip code, then try again.",
        color="danger",
        dismissable=True,  # Allows the user to close the alert
        is_open=False,  # Initially hidden
        style={'marginTop': '20px'},  # Adjust the margin as needed
        ),

    # Container for the map
    html.Div([
        dcc.Loading(
            id="loading-map", 
            children=[
                html.Div(
                    DeckGL(
                        id="map",
                        data=pdk.Deck(
                            initial_view_state=pdk.ViewState(
                                longitude=ATOCHA[0],
                                latitude=ATOCHA[1],
                                zoom=5,
                                pitch=0,
                            ),
                            layers=[],
                            map_style=CHOSEN_STYLE,                            
                        ).to_json(),
                        mapboxKey=MAPBOX_API_KEY,
                        tooltip={
                            "html": "<b>Name:</b> {name}<br><b>Street:</b> {street}<br><b>Manager:</b> {manager}<br><b>Shift:</b> {shift} <br> <b>Center:</b> {center}",
                            "style": {
                                "backgroundColor": "steelblue",
                                "color": "white"
                            }
                        }
                    ),
                    style={'height': '50vh', 'width': '100%'}  # Set the size of the map here
                )
            ], 
            type="circle"
        ),
    ], style={'width': '80%', 'position': 'relative', 'marginTop': '20px'}),  # Adjust marginTop as needed
    html.Div(id='data-tables-container', children=[], style={'width': '75%', 'position': 'relative', 'marginTop': '20px'}),  # Container for dynamic data tables
    # html.Button('Create Match', id='create-match', n_clicks=0, style={'marginTop': '20px', 'marginBottom': '20px'}),  # Button for creating matches
    # dcc.Store(id='drivers-to-match-store'),  # Store for selected drivers' IDs
], style={'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center'})  # This ensures vertical stacking and center alignment

@callback(
    [Output('map', 'data'), Output('data-tables-container', 'children'), Output('alert-fail-geoencode', 'is_open')],
    [Input('submit-val', 'n_clicks'), Input('shifts-dropdown', 'value'), Input('managers-dropdown', 'value'), Input('is-matched-radio', 'value'), Input('center-dropdown', 'value')],
    [State('street-input', 'value'),
     State('zip-code-input', 'value'),
     State('time-limit-range-slider', 'value')]
)
def update_map_and_tables(n_clicks, selected_shifts, selected_managers, is_matched_filter, selected_center, street, zip_code, time_limits):
    if n_clicks > 0:
        geoencode_result = geoencode_address(street, zip_code)
        
        if geoencode_result is None:
            # Geoencoding fails, show the alert
            return dash.no_update, dash.no_update, True  # Open the alert
        
        if geoencode_result:
            lat, lon = geoencode_result
            lat, lon = float(lat), float(lon)
            times = list(range(time_limits[0], time_limits[1] + 1, 5))
            isochrones_geojson = calculate_isochrones(lat, lon, times)
            isochrone_coords = extract_coords_from_encompassing_isochrone(isochrones_geojson)
            computed_view_state = pdk.data_utils.compute_view(isochrone_coords, view_proportion=0.9)
            drivers_df, drivers_gdf, drivers_list = fetch_drivers()
            
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

            # Define icon data
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
            # Generate data tables for each partition
            data_tables = []
            num_partitions = len(partitioned_drivers)
            for i, partition in enumerate(partitioned_drivers):
                partition = partition.drop(columns=['geometry', 'lat', 'lng'])
                table = create_data_table({'type': 'drivers-table', 'index': i}, partition, page_size=10)
                if i < num_partitions - 1:
                    number_of_drivers = len(partition)
                    iso_title = time_limits[0] + i * 5 
                    title = f'{number_of_drivers} drivers within {iso_title} minutes of chosen location'
                else:
                    # This is the last partition, so we give it a custom title
                    number_of_drivers = len(partition)
                    title = f'{number_of_drivers} drivers outside largest isochrone'
                data_tables.append(html.Div(children=[html.H3(title), table], style={'margin': '20px'}))

            return new_deck_data, data_tables, False
        else:
            # No clicks yet, do not update anything and ensure the alert is closed
            return dash.no_update, dash.no_update, False
    return dash.no_update, dash.no_update, False
