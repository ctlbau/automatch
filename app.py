import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State, callback_context
import dash_auth
from dotenv import load_dotenv
import os
import json
from flask import Flask

thisdir = os.path.dirname(__file__)
load_dotenv(os.path.join(thisdir, '.env'))

USERS = json.loads(os.getenv("USERS"))
FLASK_KEY = os.getenv("FLASK_KEY")

server = Flask(__name__)
server.secret_key = FLASK_KEY

app = dash.Dash(
    __name__,
    server=server,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css'
    ],
    use_pages=True,
    suppress_callback_exceptions=True
)

auth = dash_auth.BasicAuth(
    app,
    USERS
)

def create_sidebar():
    return html.Div([
        html.Div([
            html.Button(
                html.I(className="fas fa-bars fa-lg"),
                id="sidebar-toggle",
                className="btn btn-primary sidebar-toggle"
            ),
            html.H3("AuroPulse", className="sidebar-title"),
        ], className="sidebar-header"),
        html.Hr(),
        dbc.Nav(
            [
                dbc.NavLink(
                    [html.Div(page["name"], className="ms-2")],
                    href=page["path"],
                    active="exact",
                )
                for page in dash.page_registry.values()
            ],
            vertical=True,
            pills=True,
        ),
    ],
    id="sidebar",
    className="bg-light")

app.layout = html.Div([
    dbc.Container([
        dbc.Row([
            dbc.Col([
                html.Div(create_sidebar(), id="sidebar-container"),
            ], width=1, className="p-0 m-0"),
            dbc.Col([
                dash.page_container,
            ], id="content", width=11, className="p-0 m-0"),
        ], className="g-0"),
    ], fluid=True, className="p-0 m-0"),
    dcc.Store(id="sidebar-state", data="open")
], className="vh-100")

@callback(
    Output("sidebar", "className"),
    Output("sidebar-toggle", "className"),
    Output("sidebar-container", "className"),
    Output("content", "className", allow_duplicate=True),
    Output("sidebar-state", "data"),
    Input("sidebar-toggle", "n_clicks"),
    State("sidebar-state", "data"),
    prevent_initial_call=True
)
def toggle_sidebar(n, sidebar_state):
    if callback_context.triggered_id == "sidebar-toggle":
        if sidebar_state == "open":
            return "bg-light sidebar-closed", "btn btn-primary sidebar-toggle-closed", "sidebar-container-closed", "content-expanded", "closed"
        else:
            return "bg-light", "btn btn-primary", "", "", "open"
    
    # This case should not be reached due to prevent_initial_call=True
    return dash.no_update

# If you need to update content className based on sidebar state in other parts of your app:
@callback(
    Output("content", "className", allow_duplicate=True),
    Input("sidebar-state", "data"),
    prevent_initial_call=True
)
def update_content_class(sidebar_state):
    if sidebar_state == "closed":
        return "content-expanded"
    return ""

if __name__ == '__main__':
    app.run_server(debug=True, port=8050)
