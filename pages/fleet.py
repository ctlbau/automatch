import dash
from dash import dcc, html, callback
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from db.fleetpulse.db_support import fetch_managers, fetch_statuses, fetch_centers, fetch_vehicles, fetch_plates, select_plate, fetch_date_range, fetch_companies_ids
from ui.components import *
from utils.agg_utils import calculate_aggregations, calculate_status_periods, filter_and_format, sanity_check
from utils.geo_utils import lic_plate2sher_id_map, get_last_coordinates_by_plate, geodecode_coordinates
import pydeck as pdk
import pandas as pd

MAP_STYLES = ["mapbox://styles/mapbox/light-v9", "mapbox://styles/mapbox/dark-v9", "mapbox://styles/mapbox/satellite-v9"]
CHOSEN_STYLE = MAP_STYLES[2]
AURO = (-3.587811320499316, 40.39171586339568)


dash.register_page(__name__, path='/fleet')

layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            dbc.Tabs(
                id="fleet-tabs",
                active_tab="vehicle-tab",
                children=[
                    dbc.Tab(label="Manager View", tab_id="manager-tab"),
                    dbc.Tab(label="Vehicle View", tab_id="vehicle-tab"),
                ],
                className="mb-3 sidebar-adjacent-tabs"
            ),
            html.Div(id='fleet-tabs-content')
        ], className="p-0")
    ], className="g-0")
], fluid=True, className="p-0")

@callback(
    Output('fleet-tabs-content', 'children'),
    Input('fleet-tabs', 'active_tab')
)
def render_fleet_ui(active_tab):
    min_date, max_date = fetch_date_range()
    if active_tab == 'manager-tab':
        return create_manager_layout(min_date, max_date)
    elif active_tab == 'vehicle-tab':
        return create_vehicle_layout(min_date, max_date)



def create_manager_layout(min_date, max_date):
    center_options = fetch_centers().to_dict('records')
    status_options = fetch_statuses().to_dict('records')
    manager_options = fetch_managers().to_dict('records')
    company_options = fetch_companies_ids().to_dict('records')
    
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        create_dropdown('manager-dropdown', options=manager_options, label='name', value='name', placeholder='Select manager', multi=False, add_all=True),
                        create_dropdown('company-dropdown', options=company_options, label='company', value='ids', placeholder='Select company', multi=True, add_all=False),
                        create_dropdown('center-dropdown', options=center_options, label='name', value='id', placeholder='Select center', multi=True, add_all=False),
                        create_dropdown('status-dropdown', options=status_options, label='status', value='status', placeholder='Select status', multi=True, add_all=False),
                        create_date_range_picker('date-picker-range', min_date, max_date),
                        create_navbar_options('count-proportion-radio'),
                    ])
                ], className="mb-3"),
            ], width=3),
            dbc.Col([
                dbc.Spinner(
                    dbc.Card([
                        dbc.CardBody([
                            html.Div(id='manager-view-graph-container')
                        ])
                    ], className="mb-3", id='manager-view-graph-card', style={'display': 'none'})
                ),
            ], width=9)
        ]),
        dbc.Row([
            dbc.Col([
                html.Div(id='manager-view-table-container'),
                html.Div(id='manager-view-button-container', className="text-right mt-2")
            ], width=12)
        ], className="mt-3"),
        create_modal('details-modal-all', 'details-modal-title-all', 'modal-content-all', 'modal-footer-all'),
        create_modal('details-modal-part', 'details-modal-title-part', 'modal-content-part', 'modal-footer-part'),
    ], fluid=True)

@callback(
    [Output('manager-view-graph-container', 'children'),
     Output('manager-view-table-container', 'children'),
     Output('manager-view-button-container', 'children'),
     Output('manager-view-graph-card', 'style')],
    [
        Input('fleet-tabs', 'active_tab'),
        Input('date-picker-range', 'start_date'),
        Input('date-picker-range', 'end_date'),
        Input('company-dropdown', 'value'),
        Input('center-dropdown', 'value'),
        Input('manager-dropdown', 'value'),
        Input('status-dropdown', 'value'),
        Input('count-proportion-radio', 'value'),
    ],
    State('status-dropdown', 'options')
)
def update_managerview_components(tab, start_date, end_date, company_ids, selected_centers, selected_manager, selected_statuses, count_proportion_radio, status_options):
    if tab != 'manager-tab':
        return dash.no_update, dash.no_update, dash.no_update, {'display': 'none'}
    if company_ids == [] or company_ids is None:
        return dash.no_update, dash.no_update, dash.no_update, {'display': 'none'}

    base_df = fetch_vehicles(selected_centers, company_ids=company_ids, from_date=start_date, to_date=end_date)
    agg_df = calculate_aggregations(base_df, ['date', 'status'])
    table_page_size = len(selected_statuses) + 1 if selected_statuses else len(status_options) + 1

    if selected_manager == 'all':
        # All managers
        if selected_statuses:
            base_df = base_df[base_df['status'].isin(selected_statuses)]
            agg_df = agg_df[agg_df['status'].isin(selected_statuses)]

        pivot_df = agg_df.pivot(index='status', columns='date', values=count_proportion_radio).reset_index().fillna(0)
        total_unique_per_status = agg_df[['status', 'total_unique']].drop_duplicates()
        pivot_df = pivot_df.merge(total_unique_per_status, on='status', how='left')
        numerical_columns = pivot_df.columns[1:]
        pivot_df.loc['Total', numerical_columns] = pivot_df[numerical_columns].sum(axis=0)
        pivot_df.loc['Total', 'status'] = 'Total'
        pivot_df.reset_index(inplace=True, drop=True)
        
        for col in numerical_columns:
            pivot_df[col] = pivot_df[col].apply(lambda x: round(x, 2))
        
        csv_filename = 'all_managers_from_' + start_date + '_to_' + end_date + '.csv'
        table = create_data_table('main-table-all', pivot_df, csv_filename, table_page_size)
        download_button = html.Button('Download CSV', id='download-main-table-all-csv', n_clicks=0)
        fig = create_line_graph(agg_df, count_proportion_radio)

    else:
        if selected_manager:
            base_df = base_df[base_df['manager'] == selected_manager]
        else:
            return dash.no_update, dash.no_update, dash.no_update, {'display': 'none'}

        if selected_statuses:
            base_df = base_df[base_df['status'].isin(selected_statuses)]
        manager_agg_df = calculate_aggregations(base_df, ['date', 'status'])
        manager_pivot_df = manager_agg_df.pivot(index='status', columns='date', values=count_proportion_radio).reset_index().fillna(0)
        total_unique_per_status = manager_agg_df[['status', 'total_unique']].drop_duplicates()
        manager_pivot_df = manager_pivot_df.merge(total_unique_per_status, on='status', how='left')
        manager_pivot_df.columns = manager_pivot_df.columns.astype(str)

        csv_filename = selected_manager + '_from_' + start_date + '_to_' + end_date + '.csv'
        table = create_data_table('main-table-part', manager_pivot_df, csv_filename, table_page_size)
        download_button = html.Button('Download CSV', id='download-main-table-part-csv', n_clicks=0)
        fig = create_line_graph(manager_agg_df, count_proportion_radio)
    
    return fig, table, download_button, {'display': 'block'}

def create_vehicle_layout(min_date, max_date):
    plates_options = fetch_plates().to_dict('records')
    
    return dbc.Container([
        dcc.Store(id='plate-map-store'),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        create_dropdown('plate-dropdown', options=plates_options, label='plate', value='plate', placeholder='Select plate', multi=False, add_all=False),
                        create_date_range_picker('date-picker-range', min_date, max_date, populate_days_from_today=14),
                    ])
                ], className="mb-3"),
                html.Div(id='alert-placeholder-vehicle'),
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div(id='vehicle-view-graph-container')
                    ])
                ], className="mb-3", id='vehicle-view-graph-card', style={'display': 'none'}),
            ], width=9),
        ]),
        dbc.Row([
            dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div(
                                create_map_container('last-location-map', initial_view_coords=AURO, tooltip_info={}, map_style=CHOSEN_STYLE),
                                style={'width': '100%', 'height': '400px', 'position': 'relative'}
                            )
                        ])
                    ], className="mb-3", id='last-location-card', style={'display': 'none'}),
            ], width=12)
        ])
    ], fluid=True)

@callback(
    Output('plate-map-store', 'data'),
    Input('tabs', 'active_tab'),
    Input('url', 'pathname')
)
def update_plate_map_store(tab, pathname):
    if tab == 'vehicle-tab' or pathname == '/fleet':
        plate_map = lic_plate2sher_id_map()
        if plate_map:
            return plate_map
    return dash.no_update

@callback(
    Output('vehicle-view-graph-container', 'children'),
    Output('vehicle-view-graph-card', 'style'),
    Output('last-location-card', 'style'),
    [
        Input('plate-dropdown', 'value'),
        Input('date-picker-range', 'start_date'),
        Input('date-picker-range', 'end_date')
    ]
)
def update_vehicle_view(selected_plate, start_date, end_date):
    if not selected_plate:
        return None, {'display': 'none'}, {'display': 'none'}

    df = select_plate(plate=selected_plate, from_date=start_date, to_date=end_date)
    if df.empty:
        return None, {'display': 'none'}, {'display': 'none'}

    fig = px.line(df, x='date', y='status', title=f'Vehicle Status Over Time for vehicle {selected_plate}', markers=True)
    fig.update_layout(height=400, xaxis_tickangle=-45)
    fig.update_xaxes(tickformat="%Y-%m-%d")
    
    return dcc.Graph(figure=fig), {'display': 'block'}, {'display': 'block'}


@callback(
    Output('last-location-map', 'data'),
    Output('alert-placeholder-vehicle', 'children'),
    Input('plate-dropdown', 'value'),
    State('plate-map-store', 'data')
)
def update_map(selected_plate, plate_map):
    if not selected_plate:
        return dash.no_update, None

    if plate_map is None:
        plate_map = lic_plate2sher_id_map()
        if not plate_map:
            return dash.no_update, dbc.Alert("Failed to fetch plate map data. Please try refreshing the page.", color="danger", className="col-md-4 offset-md-4 col-12")

    if selected_plate not in plate_map:
        return dash.no_update, dbc.Alert(f"License plate '{selected_plate}' not found in Sherlog's database.", color="warning", className="col-md-4 offset-md-4 col-12")

    coords = get_last_coordinates_by_plate(selected_plate, plate_map)
    if not coords:
        return dash.no_update, dbc.Alert(f"Valid coordinates for vehicle {selected_plate} not found.", color="danger", className="col-md-4 offset-md-4 col-12")
    
    lat, lon = float(coords['lat']), float(coords['lng'])
    address = geodecode_coordinates(lat, lon)
    
    data = pd.DataFrame({
        "lat": [lat],
        "lon": [lon],
        "plate": [selected_plate],
        "address": [address] if address else ["Unknown"]
    })
    icon_data = {
        "url": "https://img.icons8.com/ios-filled/50/000000/car--v1.png",
        "width": 250,
        "height": 250,
    }

    data.loc[:, "icon_data"] = None
    for i in data.index:
        data['icon_data'] = data.apply(lambda x: icon_data, axis=1)

    icon_layer = pdk.Layer(
        type="IconLayer",
        data=data,
        get_icon="icon_data",
        get_size=8,
        size_scale=5,
        get_position=["lon", "lat"],
        pickable=True,
    )

    view_state = pdk.ViewState(
        longitude=lon,
        latitude=lat,
        zoom=16,
        pitch=0,
        bearing=0,
    )

    deck_data = pdk.Deck(
        layers=[icon_layer],
        initial_view_state=view_state,
        map_style=CHOSEN_STYLE
    ).to_json()
    return deck_data, None


@callback(
    Output('details-modal-all', 'is_open'),
    Output('details-modal-title-all', 'children'),
    Output('modal-content-all', 'children'),
    Output('modal-footer-all', 'children'),
    [
        Input('main-table-all', 'cellClicked'),
        Input('main-table-all', 'selectedRows'),
        State('company-dropdown', 'value'),
        State('center-dropdown', 'value'),
        State('date-picker-range', 'start_date'),
        State('date-picker-range', 'end_date'),
        State('status-dropdown', 'value'),
        State('count-proportion-radio', 'value'),
    ]
)
def update_modal_all(clicked_cell, clicked_row, companies, selected_centers, start_date, end_date, selected_statuses, count_proportion_radio):
    if not clicked_cell or not clicked_row:
        return False, "", [], []

    column_selected = clicked_cell['colId']
    status = clicked_row[0]['status']
    base_df = fetch_vehicles(selected_centers, company_ids=companies, from_date=start_date, to_date=end_date)
    if base_df is None or base_df.empty:
        return False, "", [], []
    
    status_df = base_df[base_df['status'] == status].copy()
    min_date = base_df['date'].min()
    max_date = base_df['date'].max()
    days = (max_date - min_date).days + 1

    if column_selected == 'total unique':
        streaks_df = calculate_status_periods(status_df)
        status_df = status_df.merge(streaks_df, on='plate', how='left')
        status_df.drop(['kendra_id','date', 'status', 'date_diff', 'status_change', 'group'], axis=1, inplace=True)
        status_df.drop_duplicates(subset=['plate'], inplace=True)
        modal_title = html.Div([
                    f"Overview of {len(status_df)} vehicles that have been in {status} status between {start_date} and {end_date}.",
                    html.Br(),
                    f"Effective days: {days}"])
        csv_filename = f'{status}_from_{start_date}_to_{end_date}.csv'
        table = create_data_table(f'modal-content-all-total-unique', status_df, csv_filename, 10)
        download_button = html.Button('Download CSV', id='download-modal-table-total-unique-csv', n_clicks=0)

        return True, modal_title, table, download_button
    
    elif column_selected == 'status':
        return False, "", [], []

    else:
        date = pd.to_datetime(column_selected).date()
        filtered_df = filter_and_format(status_df, date, status)

        if filtered_df.empty:
            return False, "", [], []

        modal_title = f"Found {len(filtered_df)} {status} vehicles on {date.strftime('%Y-%m-%d')}"
        csv_filename = f"{status}_on_{date.strftime('%Y-%m-%d')}.csv"
        table = create_data_table(f'modal-content-status', filtered_df, csv_filename, 10)
        download_button = html.Button('Download CSV', id='download-modal-table-status-csv', n_clicks=0)

    return True, modal_title, table, download_button

@callback(
    Output('details-modal-part', 'is_open'),
    Output('details-modal-title-part', 'children'),
    Output('modal-content-part', 'children'),
    Output('modal-footer-part', 'children'),
    [
        Input('main-table-part', 'cellClicked'),
        Input('main-table-part', 'selectedRows'),
        State('company-dropdown', 'value'),
        State('center-dropdown', 'value'),
        State('date-picker-range', 'start_date'),
        State('date-picker-range', 'end_date'),
        State('status-dropdown', 'value'),
        State('manager-dropdown', 'value'),
        State('count-proportion-radio', 'value'),
    ]
)
def update_modal_part(clicked_cell, clicked_row, company_ids, selected_centers, start_date, end_date, selected_statuses, selected_manager, count_proportion_radio):
    if not clicked_cell or not clicked_row:
        return False, "", [], []

    column_selected = clicked_cell['colId']
    status = clicked_row[0]['status']
    
    base_df = fetch_vehicles(selected_centers, company_ids=company_ids, from_date=start_date, to_date=end_date)
    if base_df is None or base_df.empty:
        return False, "", [], []
    
    status_df = base_df[base_df['status'] == status].copy()
    min_date = base_df['date'].min()
    max_date = base_df['date'].max()
    days = (max_date - min_date).days + 1
    
    if selected_manager:
        status_df = status_df[status_df['manager'] == selected_manager]

    if column_selected == 'total unique':
        streaks_df = calculate_status_periods(status_df)
        status_df = status_df.merge(streaks_df, on='plate', how='left')
        status_df.drop(['kendra_id','date','status', 'date_diff', 'status_change', 'group'], axis=1, inplace=True)
        status_df.drop_duplicates(subset=['plate'], inplace=True)
        modal_title = html.Div([
                    f"Overview of {len(status_df)} vehicles that have been in {status} status between {start_date} and {end_date} for {selected_manager}.",
                    html.Br(),
                    f"Effective days: {days}"])
        csv_filename = f'{status}_between_{start_date}_and_{end_date}_for_{selected_manager}.csv'
        table = create_data_table(f'modal-content-part-total-unique', status_df, csv_filename, 10)
        download_button = html.Button('Download CSV', id='download-modal-table-status-csv', n_clicks=0)

        return True, modal_title, table, download_button
    
    elif column_selected == 'status':
        return False, "", [], []

    else:
        date = pd.to_datetime(column_selected).date()
        filtered_df = filter_and_format(status_df, date, status)

        if filtered_df.empty:
            return False, "", [], []

        csv_filename = f"{status}_on_{date.strftime('%Y-%m-%d')}_for_{selected_manager}.csv"
        table = create_data_table(f'modal-content-part-date', filtered_df, csv_filename, 10)
        download_button = html.Button('Download CSV', id='download-modal-date-table', n_clicks=0)
        modal_title = f"Found {len(filtered_df)} {status} vehicles on {date.strftime('%Y-%m-%d')}"

    return True, modal_title, table, download_button

@callback(Output('modal-content-part-total-unique', 'exportDataAsCsv'),
         Input('download-modal-table-status-csv', 'n_clicks'),
         prevent_initial_call=True)
def download_csv(n_clicks):
    if n_clicks > 0:
        return True
    return dash.no_update

@callback(Output('modal-content-part-date', 'exportDataAsCsv'),
            Input('download-modal-date-table', 'n_clicks'),
            prevent_initial_call=True)
def download_csv(n_clicks):
    if n_clicks > 0:
        return True
    return dash.no_update

    
@callback(
        Output('main-table-all', 'exportDataAsCsv'),
        Input('download-main-table-all-csv', 'n_clicks')
        )
def download_csv(n_clicks):
    if n_clicks > 0:
        return True
    return dash.no_update

@callback(
        Output('main-table-part', 'exportDataAsCsv'),
        Input('download-main-table-part-csv', 'n_clicks')
        )
def download_csv(n_clicks):
    if n_clicks > 0:
        return True
    return dash.no_update

@callback(
        Output('modal-content-all-total-unique', 'exportDataAsCsv'),
        Input('download-modal-table-total-unique-csv', 'n_clicks'),
        prevent_initial_call=True
        )
def download_csv(n_clicks):
    if n_clicks > 0:
        return True
    return dash.no_update

@callback(
        Output('modal-content-status', 'exportDataAsCsv'),
        Input('download-modal-table-status-csv', 'n_clicks'),
        prevent_initial_call=True
        )
def download_csv(n_clicks):
    if n_clicks > 0:
        return True
    return dash.no_update

@callback(
    Output("content", "className", allow_duplicate=True),
    Input("sidebar-state", "data"),
    prevent_initial_call=True
)
def adjust_content(sidebar_state):
    if sidebar_state == "closed":
        return "mt-3 px-3 content-expanded"
    return "mt-3 px-3"