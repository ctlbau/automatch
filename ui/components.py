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
import numpy as np
import pandas as pd

ATOCHA = (-3.690633, 40.406785)
MAP_STYLES = ["mapbox://styles/mapbox/light-v9", "mapbox://styles/mapbox/dark-v9", "mapbox://styles/mapbox/satellite-v9"]
MAPBOX_API_KEY = os.getenv("MAPBOX_TOKEN")

def create_map_container(id, initial_view_coords, tooltip_info, map_style):
    initial_view_state = pdk.ViewState(
        longitude=initial_view_coords[0],
        latitude=initial_view_coords[1],
        zoom=5,
        pitch=0,
    )

    deck = pdk.Deck(
        initial_view_state=initial_view_state,
        map_style=map_style,
    )

    return dcc.Loading(
        id=f"loading-{id}", 
        children=[
            html.Div(
                DeckGL(
                    id=id,
                    mapboxKey=MAPBOX_API_KEY,
                    data=deck.to_json(),
                    tooltip=tooltip_info
                ),
                style={'width': '100%', 'height': '100%'}
            )
        ], 
        type="circle"
    )


# def create_navbar(title):
#     return html.Nav(
#         className="navbar navbar-expand-lg navbar-dark bg-dark mb-2",
#         children=[
#             html.Div(
#                 className="container-fluid d-flex justify-content-center",
#                 children=[
#                     html.Span(html.Strong(title), className="navbar-brand text-center")
#                 ]
#             )
#         ]
#     )

# def create_company_filter(id):
#     return html.Nav(
#         className="navbar navbar-expand-lg mb-2",
#         children=[
#             html.Div(
#                 className="container-fluid",
#                 children=[
#                     html.Div(
#                         dcc.Dropdown(
#                             id=id,
#                             options=[
#                                 {'label': 'Auro', 'value': 'auro'},
#                                 {'label': 'Cibeles', 'value': 'cibeles'},
#                                 {'label': 'Gestionados', 'value': 'gestionados'},
#                                 {'label': 'All', 'value': 'all'}
#                             ],
#                             value='all',
#                             clearable=False,
#                             placeholder="Select company"
#                         ), className="col-md-4 offset-md-4 col-12"
#                     )
#                 ]
#             )
#         ]
#     )


# def exchange_locations_dropdown(id, placeholder, multi=False):
#     return html.Nav(
#         className="navbar navbar-expand-lg mb-2",
#         children=[
#             html.Div(
#                 className="container-fluid",
#                 children=[
#                     html.Div(
#                         dcc.Dropdown(
#                             id=id,
#                             options=[],
#                             value=[],
#                             multi=multi,
#                             clearable=True,
#                             placeholder=placeholder,
#                         ), className="col-md-4 offset-md-4 col-12",
#                     )
#                 ]
#             )
#         ]
#     )

# def create_status_filter(id):
#     return html.Nav(
#         className="navbar navbar-expand-lg mb-2",
#         children=[
#             html.Div(
#                 className="container-fluid",
#                 children=[
#                     html.Div(
#                         dcc.Dropdown(
#                             id=id,
#                             options=[],  # Populated dynamically
#                             value=[],
#                             multi=True,
#                             clearable=True,
#                             placeholder="Select statuses"
#                         ), className="col-md-4 offset-md-4 col-12"
#                     )
#                 ]
#             )
#         ]
#     )

# def create_plate_filter(id):
#     return html.Nav(
#         className="navbar navbar-expand-lg mb-2",
#         children=[
#             html.Div(
#                 className="container-fluid",
#                 children=[
#                     html.Div(
#                         dcc.Dropdown(
#                             id=id,
#                             options=[],  # Populated dynamically
#                             value='',
#                             multi=False,
#                             clearable=True,
#                             placeholder="Select plates"
#                         ), className="col-md-4 offset-md-4 col-12"
#                     )
#                 ]
#             )
#         ]
#     )


# manager_filter = html.Nav(
#     className="navbar navbar-expand-lg mb-2",
#     children=[
#         html.Div(
#             className="container-fluid",
#             children=[
#                 html.Div(
#                     dcc.Dropdown(
#                         id='manager-dropdown',
#                         options=[],  # Populated dynamically
#                         value=[],
#                         multi=False,
#                         clearable=True,
#                         placeholder="Select managers"
#                     ), className="col-md-4 offset-md-4 col-12"
#                 )
#             ]
#         )
#     ]
# )


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
                        ), className='align-items-center mb-2'
                    )
                ]
            )
        ]
    )

def create_date_range_picker(id, min_date, max_date, populate_days_from_today=7):
    today = datetime.today().date()
    seven_days_prior = today - timedelta(days=populate_days_from_today)
    return html.Nav(
        className="navbar navbar-expand-lg",
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
                        ), className="form-control mb-3"
                    )
                ]
            )
        ]
    )


def create_dropdown(id, options, label='name', value='id', placeholder='Select an option', multi=False, add_all=False, class_name="", default_value=None):
    options = [{'label': option[label], 'value': ','.join(map(str, option[value])) if isinstance(option[value], list) else option[value]} for option in options]
    if add_all:
        options = [{'label': 'All', 'value': 'all'}] + options
    return dcc.Dropdown(
        id=id,
        options=options,
        value=default_value if default_value is not None else ([] if multi else None),
        multi=multi,
        clearable=True,
        placeholder=placeholder,
        className=f'dash-dropdown {class_name} form-control mb-3'
    )


def create_modal(modal_id, title_id, content_id, footer_id):
    return dbc.Modal(
        [
            dbc.ModalHeader(
                dbc.ModalTitle(id=title_id), 
                close_button=True,
                ),
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
        centered=True,
        scrollable=True,
    )

def create_data_table(id, data, filename, page_size=10, custom_height=None):
    if data.empty:
        return html.Div("No data available")
    data.columns = data.columns.astype(str)
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
            # 'tooltipShowDelay': 1,
        },
        className="ag-theme-quartz",
    )
    if custom_height is not None:
        grid.style = {'height': custom_height, 'width': '100%'}
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
    fig.update_xaxes(rangeslider_visible=True)
    fig = dcc.Graph(figure=fig)
    fig.responsive = True
    return fig



def plot_distance_histogram(df):
    df = df.copy()
    df.dropna(subset=['distance'], inplace=True)
    
    min_distance = df['distance'].min()
    max_distance = df['distance'].max()

    num_bins = 50
    bins = np.linspace(min_distance, max_distance, num_bins + 1)

    # hist_data = df.groupby(pd.cut(df['distance'], bins=bins)).agg(
    #     count=('distance', 'count'),
    #     drivers=('driver', lambda x: ', '.join(map(str, x)))
    # ).reset_index()

    hist_data = df.groupby(pd.cut(df['distance'], bins=bins), observed=True).agg(
        count=('distance', 'count'),
        drivers=('driver', lambda x: ', '.join(map(str, x)))
    ).reset_index()

    hist_data['distance'] = hist_data['distance'].astype(str)

    fig = px.bar(
        hist_data,
        x='distance',
        y='count',
        title='Distribution of Distances',
        hover_data={'drivers': True},
        category_orders={'distance': hist_data['distance']}
    )

    fig.update_traces(hovertemplate='Distance Range: %{x}<br>Count: %{y}<br>Drivers: %{customdata}')
    fig.update_layout(xaxis_title='Distance Range in Kms', yaxis_title='Count')

    return dcc.Graph(figure=fig)
