from dash import dcc, html, dash_table
from db.fleetpulse.db_support import *
from datetime import datetime, timedelta
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import dash_ag_grid as dag

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

def create_modal_window(data):
    data_table = create_data_table('modal-data-table', data)
    return html.Div([
        dbc.Button("Show Modal", id="open-modal"),
        dbc.Modal(
            [
                dbc.ModalHeader("Details"),
                dbc.ModalBody(data_table),
                dbc.ModalFooter(
                    dbc.Button("Close", id="close-modal", className="ml-auto")
            ),
        ],
        id="details-modal",
        is_open=False,
        size="xl",
    )
])

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

def create_data_table(id, data, page_size=10):
    columnDefs = [{"field": i} for i in data.columns]
    grid = dag.AgGrid(
        id=id,
        rowData=data.to_dict("records"),
        columnDefs=columnDefs,
        defaultColDef={'filter': True},
        columnSize="sizeToFit",
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
