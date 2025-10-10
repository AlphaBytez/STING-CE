import typer
app = typer.Typer(help="Group help text")

@app.callback()
def main():
    """Main CLI entry point"""
    pass

@app.command()
def install():
    """Install something"""
    pass

if __name__ == "__main__":
    app()
