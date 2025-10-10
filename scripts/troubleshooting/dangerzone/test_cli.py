import typer
app = typer.Typer(help="Group help text")
@app.command()
def install():
    """Install something"""
    pass

if __name__ == "__main__":
    app()
