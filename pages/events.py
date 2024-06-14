import dash
from dash import callback, html, dcc
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from db.events import fetch_managers, get_min_max_dates_from_schedule_events, fetch_driver_events_by_period_for_managers, fetch_driver_events_by_period_for_drivers, fetch_event_options, fetch_employees_in_schedule_event
from ui.components import create_data_table, create_modal, create_dropdown, create_date_range_picker
from utils.agg_utils import expand_events

dash.register_page(__name__, path='/events')

layout = html.Div([
    dcc.Tabs(id="event-tabs", value='manager-event-tab', children=[
        dcc.Tab(label='Manager View', value='manager-event-tab'),
        dcc.Tab(label='Driver View', value='driver-event-tab'),
    ], className="col-md-3 offset-md-1 col-12"),
    html.Div(id='event-tabs-content')
])

@callback(Output('event-tabs-content', 'children'),
          Input('event-tabs', 'value'))
def render_content(tab):
    if tab == 'manager-event-tab':
        min_date, max_date = get_min_max_dates_from_schedule_events()
        manager_options = fetch_managers().to_dict('records')
        event_options = fetch_event_options().to_dict('records')
        # event_options = [event for event in event_options if event['name'] not in ['Libre', 'Alta Medica']]
        manager_layout = dbc.Container([
            dbc.Row([
                dbc.Col([
                    create_date_range_picker('event-date-range-picker', min_date, max_date),
                    create_dropdown('manager-dropdown', options=manager_options, label='name', value='name', placeholder='Select manager', multi=True, add_all=True),
                    create_dropdown('event-dropdown', options=event_options, label='name', value='name', placeholder='Select event', multi=True, add_all=False),
                    dcc.RadioItems(
                        id='scale-toggle',
                        options=[
                            {'label': 'Counts', 'value': 'count'},
                            {'label': 'Proportional', 'value': 'proportion'}
                        ],
                        value='count',
                        labelStyle={'display': 'inline-block'}
                    ),
                    dcc.Loading(html.Div(id='manager-event-container', children=[], style={'width': '100%'}), type='circle'),
                ])
            ])
        ])
        return manager_layout
    elif tab == 'driver-event-tab':
        min_date, max_date = get_min_max_dates_from_schedule_events()
        event_options = fetch_event_options().to_dict('records') 
        driver_layout = dbc.Container([
            dbc.Row([
                dbc.Col([
                    create_date_range_picker('event-date-range-picker', min_date, max_date),
                    dcc.Loading(create_dropdown('employee-dropdown', options=[], label='name', value='id', placeholder='Select driver', multi=True, add_all=False), type='circle'),
                    create_dropdown('event-dropdown', options=event_options, label='name', value='name', placeholder='Select event', multi=True, add_all=False),
                    dcc.RadioItems(
                        id='scale-toggle',
                        options=[
                            {'label': 'Counts', 'value': 'count'},
                            {'label': 'Proportional', 'value': 'proportion'}
                        ],
                        value='count',
                        labelStyle={'display': 'inline-block'}
                    ),
                    dcc.Loading(html.Div(id='driver-event-container', children=[], style={'width': '100%'}), type='circle'),
                ])
            ])
        ])
        return driver_layout

@callback(
    Output('manager-event-container', 'children'),
    Input('event-date-range-picker', 'start_date'),
    Input('event-date-range-picker', 'end_date'),
    Input('manager-dropdown', 'value'),
    Input('event-dropdown', 'value'),
    Input('scale-toggle', 'value'),
    prevent_initial_callback=True
)
def render_manager_event_container(start_date, end_date, managers, events, scale):
    if not managers:
        return html.Div()
    if 'all' in managers:
        managers = None
    df = fetch_driver_events_by_period_for_managers(start_date, end_date, managers=managers)
    # df = df[~df['event'].isin(['Libre', 'Alta Medica'])]
    df = expand_events(df)
    df['week'] = df['date'].dt.isocalendar().week
    df = df[(df['start'] >= start_date) & (df['end'] <= end_date)]
    start_week = df['week'].min()
    end_week = df['week'].max()
    if events:
        df = df[df['event'].isin(events)]
    
    total_col = df.groupby('week').size().reset_index(name='total_count')
    dfg = df.groupby(['week', 'event']).agg({'event': 'count'}).rename(columns={'event': 'count'})
    dfg.reset_index(inplace=True)
    dfg = pd.merge(dfg, total_col, on=['week'], how='left')
    dfg['proportion'] = dfg['count'] / dfg['total_count']
    dfg['proportion'] = dfg['proportion'].apply(lambda x: round(x, 3))
    dfg = dfg.sort_values(by=scale, ascending=False)
    pivot = dfg.pivot(index=['event'], columns=['week'], values=scale).fillna(0)
    pivot = pivot.reset_index()
    
    if scale == 'count':
        numeric_cols = pivot.select_dtypes(include='number').columns
        pivot['Total'] = pivot[numeric_cols].sum(axis=1)

    page_size = len(pivot)
    grid = create_data_table('events-table', pivot, 'events.csv', page_size=page_size)

    color_map = px.colors.qualitative.Plotly
    event_colors = {event: color_map[i % len(color_map)] for i, event in enumerate(dfg['event'].unique())}

    dfg = dfg.sort_values(by=scale, ascending=False)
    bars = []
    for week in range(start_week, end_week + 1):
        week_data = dfg[dfg['week'] == week]
        bar_fig = px.bar(
            week_data,
            x=scale,
            y='event', 
            color='event',
            title=f'Event Distribution for Week {week}',
            color_discrete_map=event_colors,
            orientation='h'
        )
        bar_fig.update_layout(showlegend=False)
        bar_fig.update_layout(yaxis_title="Events")
        if scale == 'proportion':
            bar_fig.update_layout(xaxis_title="Proportion")
            bar_fig.update_layout(xaxis_tickformat=".1%")
            bar_fig.update_layout(xaxis_tickangle=-45)
        bars.append(dbc.Col(dcc.Graph(figure=bar_fig), width=6))

    global_data = df.groupby('event').agg({'event': 'count'}).rename(columns={'event': 'count'})
    global_data['proportion'] = global_data['count'] / global_data['count'].sum()
    global_data['proportion'] = global_data['proportion'].apply(lambda x: round(x, 3))
    global_data = global_data.reset_index()
    global_data = global_data.sort_values(by=scale, ascending=False)
    global_bar_fig = px.bar(
        global_data,
        x=scale,
        y='event',
        color='event',
        title=f'Global Event Distribution between {start_date} and {end_date}',
        color_discrete_map=event_colors,
        orientation='h'
    )
    global_bar_fig.update_layout(showlegend=False)
    global_bar_fig.update_layout(xaxis_type="log")
    if scale == 'count':
        global_bar_fig.update_layout(yaxis_title="Event Count")
    if scale == 'proportion':
        global_bar_fig.update_layout(xaxis_title="Event Proportion")
        global_bar_fig.update_layout(xaxis_tickformat=".1%")
        global_bar_fig.update_layout(xaxis_tickangle=-45)

    bars.append(dbc.Col(dcc.Graph(figure=global_bar_fig), width=12))

    return dcc.Loading([
        dbc.Row(bars),
        grid
    ], type='circle')


@callback(
    Output('driver-event-container', 'children'),
    Input('event-date-range-picker', 'start_date'),
    Input('event-date-range-picker', 'end_date'),
    Input('employee-dropdown', 'value'),
    Input('event-dropdown', 'value'),
    Input('scale-toggle', 'value'),
    prevent_initial_callback=True
)
def render_driver_event_container(start_date, end_date, drivers, events, scale):
    if not drivers:
        return html.Div()
    if 'all' in drivers:
        drivers = None
    df = fetch_driver_events_by_period_for_drivers(start_date, end_date, drivers)
    if df.empty:
        return html.Div()
    if events:
        df = df[df['event'].isin(events)]
    df = expand_events(df)
    df['week'] = df['date'].dt.isocalendar().week
    df = df[(df['start'] >= start_date) & (df['end'] <= end_date)]
    start_week = df['week'].min()
    end_week = df['week'].max()
    total_col = df.groupby('week').size().reset_index(name='total_count')
    dfg = df.groupby(['week', 'event']).agg({'event': 'count'}).rename(columns={'event': 'count'})
    dfg.reset_index(inplace=True)
    dfg = pd.merge(dfg, total_col, on=['week'], how='left')
    dfg['proportion'] = dfg['count'] / dfg['total_count']
    dfg['proportion'] = dfg['proportion'].apply(lambda x: round(x, 3))
    dfg = dfg.sort_values(by=scale, ascending=False)
    pivot = dfg.pivot(index=['event'], columns=['week'], values=scale).fillna(0.000)
    pivot = pivot.reset_index()
    page_size = len(pivot)
    
    if scale == 'count':
        numeric_cols = pivot.select_dtypes(include='number').columns
        pivot['Total'] = pivot[numeric_cols].sum(axis=1)

    grid = create_data_table('events-table', pivot, 'events.csv', page_size=page_size)

    color_map = px.colors.qualitative.Plotly
    event_colors = {event: color_map[i % len(color_map)] for i, event in enumerate(dfg['event'].unique())}

    bars = []
    for week in range(start_week, end_week + 1):
        week_data = dfg[dfg['week'] == week]
        bar_fig = px.bar(
            week_data,
            x=scale,
            y='event', 
            color='event',
            title=f'Event Distribution for Week {week}',
            color_discrete_map=event_colors,
            orientation='h'
        )
        bar_fig.update_layout(showlegend=False)
        bar_fig.update_layout(yaxis_title="Events")
        bar_fig.update_layout(xaxis_type="log")
        if scale == 'proportion':
            bar_fig.update_layout(xaxis_title="Proportion")
            bar_fig.update_layout(xaxis_tickformat=".1%")
            bar_fig.update_layout(xaxis_tickangle=-45)
        bars.append(dbc.Col(dcc.Graph(figure=bar_fig), width=6))

    global_data = df.groupby('event').agg({'event': 'count'}).rename(columns={'event': 'count'})
    global_data['proportion'] = global_data['count'] / global_data['count'].sum()
    global_data['proportion'] = global_data['proportion'].apply(lambda x: round(x, 3))
    global_data = global_data.reset_index()
    global_data = global_data.sort_values(by=scale, ascending=False)
    global_bar_fig = px.bar(
        global_data,
        x=scale,
        y='event',
        color='event',
        title=f'Global Event Distribution between {start_date} and {end_date}',
        color_discrete_map=event_colors,
        orientation='h'
    )
    global_bar_fig.update_layout(showlegend=False)
    global_bar_fig.update_layout(xaxis_type="log")
    if scale == 'count':
        global_bar_fig.update_layout(yaxis_title="Event Count")
    if scale == 'proportion':
        global_bar_fig.update_layout(xaxis_title="Event Proportion")
        global_bar_fig.update_layout(xaxis_tickformat=".1%")
        global_bar_fig.update_layout(xaxis_tickangle=-45)

    bars.append(dbc.Col(dcc.Graph(figure=global_bar_fig), width=12))

    return dcc.Loading([
        dbc.Row(bars),
        grid
    ], type='circle')

@callback(
    Output('employee-dropdown', 'options'),
    Input('event-date-range-picker', 'start_date'),
    Input('event-date-range-picker', 'end_date')
)
def update_driver_options(start_date, end_date):
    if not start_date or not end_date:
        return []
    df = fetch_employees_in_schedule_event(start_date, end_date)
    df.sort_values(by='name', inplace=True)
    driver_options = df.to_dict('records')
    driver_options = [{'label': driver['name'], 'value': driver['id']} for driver in driver_options]
    driver_options.insert(0, {'label': 'All drivers', 'value': 'all'})
    return driver_options