import click

from eznet import Inventory


@click.command()
@click.option(
    "--inventory", "-i", required=True, type=click.types.Path(exists=True)
)
def main(inventory: str) -> None:
    print(Inventory().load(inventory).export_as_rundeck())


if __name__ == "__main__":
    main()
