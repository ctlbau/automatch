from dash import dcc, html
from db.fleetpulse.db_support import fetch_managers, fetch_statuses, fetch_date_range, fetch_centers
from datetime import datetime, timedelta
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import dash_ag_grid as dag
import pydeck as pdk
from dash_deck import DeckGL
import os

ATOCHA = (-3.690633, 40.406785)
MAP_STYLES = ["mapbox://styles/mapbox/light-v9", "mapbox://styles/mapbox/dark-v9", "mapbox://styles/mapbox/satellite-v9"]
CHOSEN_STYLE = MAP_STYLES[0]
MAPBOX_API_KEY = os.getenv("MAPBOX_TOKEN")


def create_map_container(id):
        return html.Div([
            dcc.Loading(
                id="loading-map", 
                children=[
                    html.Div(
                        DeckGL(
                            id=id,
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
                                "html": "<b>Name:</b> {name}<br><b>Street:</b> {street}<br><b>Manager:</b> {manager}<br><b>Shift:</b> {shift} <br> <b>Center:</b> {center}, <b>Matched:</b> {is_matched} <br> <b>Matched With:</b> {matched_with} <br> <b>Exchange Location:</b> {exchange_location}",
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
        ], style={'width': '80%', 'position': 'relative', 'marginTop': '20px'})


def create_navbar(title):
    return html.Nav(
        className="navbar navbar-expand-lg navbar-dark bg-dark mb-2",
        children=[
            html.Div(
                className="container-fluid d-flex justify-content-center",
                children=[
                    html.Span(html.Strong(title), className="navbar-brand text-center")
                ]
            )
        ]
    )

def create_company_filter(id):
    return html.Nav(
        className="navbar navbar-expand-lg mb-2",
        children=[
            html.Div(
                className="container-fluid",
                children=[
                    html.Div(
                        dcc.Dropdown(
                            id=id,
                            options=[
                                {'label': 'Auro', 'value': 'auro'},
                                {'label': 'Cibeles', 'value': 'cibeles'},
                                {'label': 'Gestionados', 'value': 'gestionados'},
                                {'label': 'All', 'value': 'all'}
                            ],
                            value='all',
                            clearable=False,
                            placeholder="Select company"
                        ), className="col-md-4 offset-md-4 col-12"
                    )
                ]
            )
        ]
    )

def create_dropdown(id, options, placeholder, multi=False):
    return html.Nav(
        className="navbar navbar-expand-lg mb-2",
        children=[
            html.Div(
                className="container-fluid",
                children=[
                    html.Div(
                        dcc.Dropdown(
                            id=id,
                            options=label_value_from_dict(options),
                            value=[],
                            multi=multi,
                            clearable=True,
                            placeholder=placeholder,
                        ), className="col-md-4 offset-md-4 col-12",
                    )
                ]
            )
        ]
    )

def label_value_from_dict(data):
    return [{'label': data['name'], 'value': data['id']} for data in data]


def exchange_locations_dropdown(id, placeholder, multi=False):
    return html.Nav(
        className="navbar navbar-expand-lg mb-2",
        children=[
            html.Div(
                className="container-fluid",
                children=[
                    html.Div(
                        dcc.Dropdown(
                            id=id,
                            options=[],
                            value=[],
                            multi=multi,
                            clearable=True,
                            placeholder=placeholder,
                        ), className="col-md-4 offset-md-4 col-12",
                    )
                ]
            )
        ]
    )

def create_status_filter(id):
    return html.Nav(
        className="navbar navbar-expand-lg mb-2",
        children=[
            html.Div(
                className="container-fluid",
                children=[
                    html.Div(
                        dcc.Dropdown(
                            id=id,
                            options=[],  # Populated dynamically
                            value=[],
                            multi=True,
                            clearable=True,
                            placeholder="Select statuses"
                        ), className="col-md-4 offset-md-4 col-12"
                    )
                ]
            )
        ]
    )

def create_plate_filter(id):
    return html.Nav(
        className="navbar navbar-expand-lg mb-2",
        children=[
            html.Div(
                className="container-fluid",
                children=[
                    html.Div(
                        dcc.Dropdown(
                            id=id,
                            options=[],  # Populated dynamically
                            value='',
                            multi=False,
                            clearable=True,
                            placeholder="Select plates"
                        ), className="col-md-4 offset-md-4 col-12"
                    )
                ]
            )
        ]
    )

def create_date_range_picker(id):
    today = datetime.today().date()
    seven_days_prior = today - timedelta(days=7)
    min_date, max_date = fetch_date_range()
    return html.Nav(
        className="navbar navbar-expand-lg mb-2",
        children=[
            html.Div(
                className="container-fluid",
                children=[
                    html.Div(
                        dcc.DatePickerRange(
                            id=id,
                            start_date=seven_days_prior,
                            end_date=today,
                            min_date_allowed=min_date,
                            max_date_allowed=max_date,
                            display_format='D MMM YY',
                        ), className="col-md-4 offset-md-4 col-12"
                    )
                ]
            )
        ]
    )


manager_filter = html.Nav(
    className="navbar navbar-expand-lg mb-2",
    children=[
        html.Div(
            className="container-fluid",
            children=[
                html.Div(
                    dcc.Dropdown(
                        id='manager-dropdown',
                        options=[],  # Populated dynamically
                        value=[],
                        multi=False,
                        clearable=True,
                        placeholder="Select managers"
                    ), className="col-md-4 offset-md-4 col-12"
                )
            ]
        )
    ]
)


def create_navbar_options(count_or_proportion_id):
    return html.Nav(
        className="navbar navbar-expand-lg mb-2",
        children=[
            html.Div(
                className="container-fluid",
                children=[
                    html.Div(
                        dcc.RadioItems(
                            id=count_or_proportion_id,
                            options=[
                                {'label': 'Count', 'value': 'count'},
                                {'label': 'Proportion', 'value': 'proportion'}
                            ],
                            value='count',
                            inline=True
                        ), className="col-md-4 offset-md-4 col-12"
                    )
                ]
            )
        ]
    )


def create_modal(modal_id, title_id, content_id, footer_id):
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle(id=title_id), close_button=True,),
            dbc.ModalBody(
                html.Div(id=content_id)
            ),
            dbc.ModalFooter(
                html.Div(id=footer_id)
            )
        ],
        id=modal_id,
        is_open=False,
        size="xl",
        # fullscreen=True,
        centered=True,
        scrollable=True,
    )

def create_data_table(id, data, filename, page_size=10, custom_height=None):
    # remove _ from column names
    data.columns = data.columns.str.replace('_', ' ')
    columnDefs = [{"field": i} for i in data.columns]
    grid = dag.AgGrid(
        id=id,
        rowData=data.to_dict("records"),
        columnDefs=columnDefs,
        defaultColDef={'filter': True},
        columnSize="sizeToFit",
        csvExportParams={'fileName': filename},
        dashGridOptions=
        {
            'pagination': True,
            'paginationPageSize': page_size,
            'animateRows': True, 
            'enableCellTextSelection': True,
            'rowSelection': 'single',
        },
        className="ag-theme-quartz",
    )
    if custom_height is not None:
        grid.style = {'height': custom_height}
    return grid

def create_grouped_graph(data, values_type):
    fig = go.Figure()
    for status in data['status'].unique():
        df_filtered = data[data['status'] == status]
        fig.add_trace(go.Bar(
                x=df_filtered['date'],
                y=df_filtered[values_type],
                name=status,
            ))

        fig.update_layout(
            barmode='group',
            xaxis_tickangle=-45,
            height=800,
            yaxis=dict(type='log')
        )
        fig.update_xaxes(tickformat="%Y-%m-%d")
    return dcc.Graph(figure=fig)

def create_line_graph(data, values_type):
    fig = px.line(data,
                  x='date',
                  y=values_type,
                  color='status',
                  markers=True)
    fig.update_layout(height=400, xaxis_tickangle=-45, yaxis=dict(type='log'))
    fig.update_xaxes(tickformat="%Y-%m-%d")
    return dcc.Graph(figure=fig)


def create_arc_layer(drivers_gdf):
    arc_data = []
    for _, row in drivers_gdf[drivers_gdf['is_matched'] == True].iterrows():
        driver_coords = row['geometry']
        matched_driver_id = row['matched_driver_id']
        if pd.notna(matched_driver_id):
            matched_driver = drivers_gdf[drivers_gdf['driver_id'] == matched_driver_id]
            if not matched_driver.empty:
                matched_driver_coords = matched_driver['geometry'].values[0]
                arc_data.append({
                    'from': [driver_coords.x, driver_coords.y],
                    'to': [matched_driver_coords.x, matched_driver_coords.y],
                    'driver_id': row['driver_id'],
                    'matched_driver_id': matched_driver_id
                })

    arc_layer = pdk.Layer(
        "ArcLayer",
        data=arc_data,
        get_source_position="from",
        get_target_position="to",
        get_width=2,
        get_tilt=15,
        get_source_color=[64, 255, 0],
        get_target_color=[0, 128, 200],
        pickable=True,
        auto_highlight=True
    )

    return pdk.Deck(layers=[arc_layer]).to_json()


def create_path_layer(drivers_gdf):
    path_data = []
    for _, row in drivers_gdf[drivers_gdf['is_matched'] == True].iterrows():
        if pd.notna(row['path']):
            path_data.append({
                'path': [[lon, lat] for lon, lat in row['path'].coords],
                'driver_id': row['driver_id'],
                'matched_driver_id': row['matched_driver_id']
            })
    
    path_df = pd.DataFrame(path_data)
    path_layer = pdk.Layer(
        "PathLayer",
        data=path_df,
        get_path="path",
        get_width=5,
        get_color=[64, 255, 0],
        pickable=True,
    )

    return pdk.Deck(layers=[path_layer]).to_json()  