import pandas as pd
import dash
from dash import dcc, html, dash_table, callback
from dash.dependencies import Input, Output, State
import plotly.express as px
import dash_bootstrap_components as dbc
from db.fleetpulse.db_support import *
from ui.components import *
import json
from utils.agg_utils import calculate_aggregations, calculate_status_periods, filter_and_format, sanity_check

dash.register_page(__name__, path='/fleet')

######## Begin Layout ##########
layout = html.Div([
    # create_navbar('Fleet Pulse'),
    dcc.Tabs(id="tabs", value='manager-tab', children=[
        dcc.Tab(label='Manager View', value='manager-tab'),
        dcc.Tab(label='Vehicle view', value='vehicle-tab'),
    ], className="col-md-2 offset-md-1 col-12"),
    html.Div(id='tabs-content'),
])
######## End Layout ############


############ Begin Render UI ############
@callback(
    Output('tabs-content', 'children'),
    [
        Input('tabs', 'value')
    ]
)
def render_ui(tab):
    if tab == 'manager-tab':
        return [
            manager_filter,
            create_company_filter('company-dropdown'),
            create_status_filter('status-dropdown'),
            create_date_range_picker('date-picker-range'),
            create_navbar_options('count-proportion-radio'),
            html.Div(id='manager-view-graph-and-table-container', className="col-md-9 offset-md-2 col-12"),
            create_modal('details-modal-all', 'details-modal-title-all', 'modal-content-all', 'modal-footer-all'),
            create_modal('details-modal-part', 'details-modal-title-part', 'modal-content-part', 'modal-footer-part'),
        ]
    elif tab == 'vehicle-tab':
        return [
            create_plate_filter('plate-dropdown'),
            create_date_range_picker('date-picker-range'),
            html.Div(id='vehicle-view-graph-container', className="col-md-9 offset-md-2 col-12")
        ]
########## End Render UI ###########

@callback(
    Output('manager-view-graph-and-table-container', 'children'),
    [
        Input('tabs', 'value'),
        Input('date-picker-range', 'start_date'),
        Input('date-picker-range', 'end_date'),
        Input('company-dropdown', 'value'),
        Input('manager-dropdown', 'value'),
        Input('status-dropdown', 'value'),
        Input('count-proportion-radio', 'value'),
    ],
    [State('status-dropdown', 'options')]
)
def update_managerview_table_and_graph(tab, start_date, end_date, selected_company, selected_manager, selected_statuses, count_proportion_radio, status_options):
    if tab != 'manager-tab':
        return dash.no_update

    base_df = fetch_vehicles(company=selected_company, from_date=start_date, to_date=end_date)
    agg_df = calculate_aggregations(base_df, ['date', 'status'])
    table_page_size = len(selected_statuses) if selected_statuses else len(status_options)

    if 'all' == selected_manager:

        if selected_statuses:
            base_df = base_df[base_df['status'].isin(selected_statuses)]
            agg_df = agg_df[agg_df['status'].isin(selected_statuses)]

        pivot_df = agg_df.pivot(index='status', columns='date', values=count_proportion_radio).reset_index().fillna(0)
        total_unique_per_status = agg_df[['status', 'total_unique']].drop_duplicates()
        pivot_df = pivot_df.merge(total_unique_per_status, on='status', how='left')
        pivot_df.columns = pivot_df.columns.astype(str)
        pivot_columns = pivot_df.columns[1:]
        for col in pivot_columns:
            pivot_df[col] = pivot_df[col].apply(lambda x: round(x, 3))

        table = create_data_table('main-table-all', pivot_df, table_page_size)
        fig = create_line_graph(agg_df, count_proportion_radio) # There is also an option for a grouped bar graph

        return [fig, table]

    else:

        if selected_manager:
            base_df = base_df[base_df['manager'] == selected_manager]
        else:
            return dash.no_update

        if selected_statuses:
            base_df = base_df[base_df['status'].isin(selected_statuses)]
        manager_agg_df = calculate_aggregations(base_df, ['date', 'status'])
        manager_pivot_df = manager_agg_df.pivot(index='status', columns='date', values=count_proportion_radio).reset_index().fillna(0)
        total_unique_per_status = manager_agg_df[['status', 'total_unique']].drop_duplicates()
        manager_pivot_df = manager_pivot_df.merge(total_unique_per_status, on='status', how='left')
        manager_pivot_df.columns = manager_pivot_df.columns.astype(str)

        table = create_data_table('main-table-part', manager_pivot_df, table_page_size)
        fig = create_line_graph(manager_agg_df, count_proportion_radio)

        return [fig, table]



@callback(
    Output('vehicle-view-graph-container', 'children'),
    [
        Input('tabs', 'value'),
        Input('plate-dropdown', 'value'),
        Input('date-picker-range', 'start_date'),
        Input('date-picker-range', 'end_date')
    ]
)
def update_vehicle_view(tab, selected_plate, start_date, end_date):
    if tab != 'vehicle-tab':
        return dash.no_update

    df = select_plate(
        plate=selected_plate,
        from_date=start_date,
        to_date=end_date
    )

    # Create a line graph showing the status of the vehicle over time
    fig = px.line(df, x='date', y='status', title='Vehicle Status Over Time', markers=True)
    fig.update_layout(height=400, xaxis_tickangle=-45)
    fig.update_xaxes(tickformat="%Y-%m-%d")

    return dbc.Row([dbc.Col(dcc.Graph(figure=fig), width=12)])


@callback(
    Output('details-modal-all', 'is_open'),
    Output('details-modal-title-all', 'children'),
    Output('modal-content-all', 'children'),
    [
        Input('main-table-all', 'active_cell'),
        State('company-dropdown', 'value'),
        State('date-picker-range', 'start_date'),
        State('date-picker-range', 'end_date'),
        State('status-dropdown', 'value'),
        State('count-proportion-radio', 'value'),
    ]
)
def update_modal_all(active_cell, companies, start_date, end_date, selected_statuses, count_proportion_radio):
    if not active_cell:
        return False, "", []

    base_df = fetch_vehicles(company=companies, from_date=start_date, to_date=end_date)
    agg_df = calculate_aggregations(base_df, ['date', 'status'])

    if base_df is None or agg_df is None:
        return False, "", []

    if selected_statuses:
        base_df = base_df[base_df['status'].isin(selected_statuses)]
        agg_df = calculate_aggregations(base_df, ['date', 'status'])

    pivot_df = agg_df.pivot(index='status', columns='date', values='count').reset_index().fillna(0)
    total_unique_per_status = agg_df[['status', 'total_unique']].drop_duplicates()
    pivot_df = pivot_df.merge(total_unique_per_status, on='status', how='left')

    column_id = active_cell['column_id']

    if column_id == 'total_unique':
        # Handle clicks on 'total_unique' cell
        status = pivot_df.iloc[active_cell['row']]['status']
        # Filter base_df for the selected status, ignoring specific date
        filtered_df = base_df[base_df['status'] == status].copy()
        
        # Aggregating detailed data for the status
        streaks_df = calculate_status_periods(filtered_df)
        
        modal_title = f"Overview of {status} vehicles from {start_date} to {end_date}"
        table = create_data_table(f'modal-content-all-overview-{status}', streaks_df, 10)

        return True, modal_title, table

    elif column_id != 'status':
        # Handle clicks on date cells
        date = pd.to_datetime(column_id).date()
        status = pivot_df.iloc[active_cell['row']]['status']
        filtered_df = filter_and_format(base_df, date, status)

        if filtered_df.empty:
            return False, "", []

        table = create_data_table(f'modal-content-all-{column_id}-{status}', filtered_df, 10)
        modal_title = f"Found {len(filtered_df)} {status} vehicles on {date.strftime('%Y-%m-%d')}"

        return True, modal_title, table

    else:
        # Clicked on the 'status' column or other non-relevant column
        return False, "", []


@callback(
    Output('details-modal-part', 'is_open'),
    Output('details-modal-title-part', 'children'),
    Output('modal-content-part', 'children'),
    [
        Input('main-table-part', 'active_cell'),
        State('company-dropdown', 'value'),
        State('date-picker-range', 'start_date'),
        State('date-picker-range', 'end_date'),
        State('manager-dropdown', 'value'),
        State('status-dropdown', 'value'),
        State('count-proportion-radio', 'value'),
    ]
)
def update_modal_part(active_cell, companies, start_date, end_date, selected_manager, selected_statuses, count_proportion_radio):
    if not active_cell:
        return False, "", []

    base_df = fetch_vehicles(company=companies, from_date=start_date, to_date=end_date)

    if base_df is None or base_df.empty:
        return False, "No data has been fetched.", []

    base_df = base_df[base_df['manager'] == selected_manager]

    if selected_statuses:
        base_df = base_df[base_df['status'].isin(selected_statuses)]

    agg_df = calculate_aggregations(base_df, ['date', 'status'])

    pivot_df = agg_df.pivot(index='status', columns='date', values='count').reset_index().fillna(0)
    total_unique_per_status = agg_df[['status', 'total_unique']].drop_duplicates()
    pivot_df = pivot_df.merge(total_unique_per_status, on='status', how='left')
    # active_cell['column_id'] gives the date as a string directly
    column_id = active_cell['column_id']

    if column_id == 'total_unique':
        # Handle clicks on 'total_unique' cell
        status = pivot_df.iloc[active_cell['row']]['status']
        # Filter base_df for the selected status, ignoring specific date
        filtered_df = base_df[base_df['status'] == status].copy()
        
        # Aggregating detailed data for the status
        streaks_df = calculate_status_periods(filtered_df)
        
        modal_title = f"Overview of {status} vehicles from {start_date} to {end_date}"
        table = create_data_table(f'modal-content-all-overview-{status}', streaks_df, 10)

        return True, modal_title, table

    elif column_id != 'status':
        # Handle clicks on date cells
        date = pd.to_datetime(column_id).date()
        status = pivot_df.iloc[active_cell['row']]['status']
        filtered_df = filter_and_format(base_df, date, status)

        if filtered_df.empty:
            return False, "", []

        table = create_data_table(f'modal-content-all-{column_id}-{status}', filtered_df, 10)
        modal_title = f"Found {len(filtered_df)} {status} vehicles on {date.strftime('%Y-%m-%d')}"

        return True, modal_title, table

    else:
        # Clicked on the 'status' column or other non-relevant column
        return False, "", []


# Perform the sanity check if count-proportion-radio is set to 'count'
# if count_proportion_radio == 'count':
#     filtered_agg_df = agg_df.loc[(agg_df['status'] == status) & (pd.to_datetime(agg_df['date']).dt.date == date)]
#     expected_count = 0 if filtered_agg_df.empty else filtered_agg_df['count'].iloc[0]
#     sanity_check_result = sanity_check(expected_count, len(filtered_df))
# if sanity_check_result:
#     return True, "", sanity_check_result


########## Begin Dropdown Options ##########
@callback(
    [Output('manager-dropdown', 'options'),
     Output('status-dropdown', 'options')],
    [Input('tabs', 'value')]
)
def set_in_managerview_manager_and_status_dropdown(tab):
    statuses = fetch_statuses()
    managers = fetch_managers()
    status_options = [
        {'label': status, 'value': status} for status in statuses['status']
        ]
    manager_options = [
            {'label': manager, 'value': manager} for manager in managers['name']
            ]
    manager_options.append({'label': 'All Managers', 'value': 'all'})

    if tab != 'manager-tab':
        return [], []
    return manager_options, status_options

@callback(
    Output('plate-dropdown', 'options'),
    [Input('tabs', 'value')]
)
def update_plate_dropdown(tab):
    if tab != 'vehicle-tab':
        return dash.no_update

    plates = fetch_plates()

    plate_options = [{'label': plate, 'value': plate} for plate in plates['plate']]

    return plate_options
########## End Dropdown Options ##########