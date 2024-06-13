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
    dcc.Tabs(id="event-tabs", value='driver-event-tab', children=[
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
        event_options = [event for event in event_options if event['name'] not in ['Libre', 'Alta Medica']]
        manager_layout = dbc.Container([
            dbc.Row([
                dbc.Col([
                    create_date_range_picker('event-date-range-picker', min_date, max_date),
                    create_dropdown('manager-dropdown', options=manager_options, label='name', value='name', placeholder='Select manager', multi=True, add_all=True),
                    create_dropdown('event-dropdown', options=event_options, label='name', value='name', placeholder='Select event', multi=True, add_all=False),
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
                        value='proportion',
                        labelStyle={'display': 'inline-block'}
                    ),
                    dcc.Loading(html.Div(id='driver-event-container', children=[], style={'width': '100%'}), type='circle'),
                ])
            ])
        ])
        return driver_layout

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
    pivot = dfg.pivot(index=['event'], columns=['week'], values=scale).fillna(0.000)
    pivot = pivot.reset_index()
    page_size = len(pivot)
    
    if scale == 'count':
        numeric_cols = pivot.select_dtypes(include='number').columns
        pivot['Total'] = pivot[numeric_cols].sum(axis=1)

    grid = create_data_table('events-table', pivot, 'events.csv', page_size=page_size)

    color_map = px.colors.qualitative.Plotly
    event_colors = {event: color_map[i % len(color_map)] for i, event in enumerate(dfg['event'].unique())}

    histograms = []
    for week in range(start_week, end_week + 1):
        week_data = dfg[dfg['week'] == week]
        hist_fig = px.bar(
            week_data,
            x='event',
            y=scale, 
            color='event',
            title=f'Event Distribution for Week {week}',
            color_discrete_map=event_colors
        )
        hist_fig.update_layout(yaxis_type="log", showlegend=False)
        hist_fig.update_layout(yaxis_title="Event Count")
        if scale == 'proportion':
            hist_fig.update_layout(yaxis_title="Proportion")
            hist_fig.update_layout(yaxis_tickformat=".1%")
        histograms.append(dbc.Col(dcc.Graph(figure=hist_fig), width=6))

    global_hist_fig = px.bar(
        dfg,
        x='event',
        y=scale,
        color='event',
        title=f'Global Event Distribution between {start_date} and {end_date}',
        color_discrete_map=event_colors
    )
    if scale == 'count':
        global_hist_fig.update_layout(yaxis_type="log", showlegend=False)
    global_hist_fig.update_layout(yaxis_title="Event Count")
    if scale == 'proportion':
        global_hist_fig.update_layout(yaxis_type="log", showlegend=False)
        global_hist_fig.update_layout(yaxis_title="Proportion")
        global_hist_fig.update_layout(yaxis_tickformat=".1%")

    histograms.append(dbc.Col(dcc.Graph(figure=global_hist_fig), width=12))

    return [
        dbc.Row(histograms),
        grid
    ]


@callback(
    Output('manager-event-container', 'children'),
    Input('event-date-range-picker', 'start_date'),
    Input('event-date-range-picker', 'end_date'),
    Input('manager-dropdown', 'value'),
    Input('event-dropdown', 'value'),
    prevent_initial_callback=True
)
def render_manager_event_container(start_date, end_date, managers, events):
    if not managers:
        return html.Div()
    df = fetch_driver_events_by_period_for_managers(start_date, end_date, managers=managers)
    df = df[~df['event'].isin(['Libre', 'Alta Medica'])]
    df = expand_events(df)
    df['week'] = df['date'].dt.isocalendar().week
    df = df[(df['start'] >= start_date) & (df['end'] <= end_date)]
    start_week = df['week'].min()
    end_week = df['week'].max()
    if events:
        df = df[df['event'].isin(events)]
    dfg = df.groupby(['week', 'event']).agg({'event': 'count'}).rename(columns={'event': 'event_count'})
    dfg.reset_index(inplace=True)
    pivot = dfg.pivot(index=['event'], columns=['week'], values='event_count').fillna(0)
    pivot = pivot.reset_index()
    pivot = pivot.sort_values(by=['event'])
    
    numeric_cols = pivot.select_dtypes(include='number').columns
    pivot['Total'] = pivot[numeric_cols].sum(axis=1)
    
    grid = create_data_table('events-table', pivot, 'events.csv')
    
    color_map = px.colors.qualitative.Plotly
    event_colors = {event: color_map[i % len(color_map)] for i, event in enumerate(dfg['event'].unique())}
    
    line_fig = px.line(
        dfg,
        x='week',
        y='event_count',
        color='event',
        title=f'Event Count from week {start_week} to {end_week}',
        color_discrete_map=event_colors
    )

    line_fig.update_layout(
        xaxis_title="Week",
        yaxis_title="Event Count",
        yaxis_type="log",
        xaxis_tickangle=-45,
        showlegend=False,
        xaxis_rangeslider_visible=True
    )

    pie_fig = px.pie(
        dfg,
        values='event_count',
        names='event',
        color='event',
        color_discrete_map=event_colors
    )

    return [
        dbc.Row([
            dbc.Col(dcc.Graph(figure=line_fig), width=6),
            dbc.Col(dcc.Graph(figure=pie_fig), width=6)
        ]),
        grid
    ]