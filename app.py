import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output
from ui.components import create_navbar
import dash_auth
from dotenv import load_dotenv
import os
import json
# Import your page layouts and callbacks
load_dotenv('.env')
users = json.loads(os.getenv("USERS"))

# Choose a theme from https://bootswatch.com/ or use the default Bootstrap theme
app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.SPACELAB, 'https://codepen.io/chriddyp/pen/bWLwgP.css'],
    use_pages=True,
    suppress_callback_exceptions=True
                )

server = app.server

auth = dash_auth.BasicAuth(
    app,
    users
)


# styling the sidebar
SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "18rem",
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

app.layout = dbc.Container([
    html.Br(),
    dbc.Row(
        [
            dbc.Col(
                [
                    sidebar
                ], xs=12, sm=12, md=2, lg=2, xl=2, xxl=2
            ),
            dbc.Col(
                [
                    dash.page_container
                ], xs=12, sm=12, md=12, lg=12, xl=12, xxl=12
            )
        ],
    )
],
fluid=True,
)


if __name__ == '__main__':
    app.run_server(debug=True)