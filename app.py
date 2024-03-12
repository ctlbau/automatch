import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output

# Import your page layouts and callbacks

# Choose a theme from https://bootswatch.com/ or use the default Bootstrap theme
app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    use_pages=True,
    suppress_callback_exceptions=True
                )

app.layout = html.Div([
    dcc.Store(id='drivers-to-match-store'),  # Store here to share data between pages
        html.H1('AutoMatch'),
    html.Div([
        html.Div(
            dcc.Link(f"{page['name']} - {page['path']}", href=page["relative_path"])
        ) for page in dash.page_registry.values()
    ]),
    dash.page_container
])

if __name__ == '__main__':
    app.run_server(debug=True)