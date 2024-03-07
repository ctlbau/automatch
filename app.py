import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output

# Choose a theme from https://bootswatch.com/ or use the default Bootstrap theme
app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    use_pages=True,
    suppress_callback_exceptions=True
                )

app.layout = dbc.Container([
    html.H1('AutoMatch'),
    html.Hr(),
    html.Div([
        html.Div(
            dcc.Link(f"{page['name']}", href=page["relative_path"])
        ) for page in dash.page_registry.values()
    ]),
      # Store here to share data between pages
    dcc.Store(id='drivers-to-match-store', data=[], storage_type='memory'), 
    dash.page_container,
])


if __name__ == '__main__':
    app.run_server(debug=True)