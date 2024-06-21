import dash
import dash_bootstrap_components as dbc
from dash import html
import dash_auth
from dotenv import load_dotenv
import os
import json
from flask import Flask

thisdir = os.path.dirname(__file__)
load_dotenv(os.path.join(thisdir, '.env'))

USERS = json.loads(os.getenv("USERS"))
FLASK_KEY = os.getenv("FLASK_KEY")

# Choose a theme from https://bootswatch.com/ or use the default Bootstrap theme
server = Flask(__name__)
server.secret_key = FLASK_KEY

app = dash.Dash(
    __name__,
    server=server,
    external_stylesheets=[dbc.themes.SPACELAB, 'https://codepen.io/chriddyp/pen/bWLwgP.css'],
    use_pages=True,
    suppress_callback_exceptions=True
                )

auth = dash_auth.BasicAuth(
    app,
    USERS
)

# styling the sidebar
SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "17rem",
    "padding": "2rem 1rem",
    "background-color": "#f8f9fa",
}

# padding for the page content
CONTENT_STYLE = {
    "margin-left": "18rem",
    "margin-right": "2rem",
    "padding": "2rem 1rem",
}

sidebar_title = html.H2("AuroPulse", className="display-4")
nav_links = [
    dbc.NavLink(
        [
            html.Div(page["name"], className="ms-2")
        ],
        href=page["path"],
        active="exact",
    )
    for page in dash.page_registry.values()
]

# Sidebar_title is wrapped in a list to allow concatenation with nav_links
sidebar_content = [sidebar_title] + nav_links

# Use sidebar_content as the children for dbc.Nav
sidebar = dbc.Nav(
    sidebar_content,
    vertical=True,
    pills=True,
    className="bg-light",
    style=SIDEBAR_STYLE
)

app.layout = html.Div([
    dbc.Container([
        dbc.Row([
            dbc.Col([
                sidebar
            ], width=2, className="position-fixed"),  # Fixed position sidebar
            dbc.Col([
                html.Div(dash.page_container, style=CONTENT_STYLE)
            ], width=10, className="offset-2")  # Main content, offset by sidebar width
        ])
    ], fluid=True)
], style={"overflow-x": "hidden"})  # Prevent horizontal scrollbar

if __name__ == '__main__':
    app.run_server(debug=True, port=8050)