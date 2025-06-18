import pathlib

from rich.console import Console

console = Console()
console.print('\nPra rodar comandos: [bold]make <comando>[/bold]')


help_file = pathlib.Path('./Makefile')
with help_file.open('r', encoding='utf-8') as file:
    groups = []
    for line in file.readlines():
        if line.find('##') >= 0:
            if line.find('@') >= 0:
                to_print = line.split('@')[-1].strip().capitalize()
                groups.append({'name': to_print, 'items': []})
            else:
                values = line.split('##')
                target = values[0]
                description = values[-1].strip().capitalize()
                target = target.split(':')[0].strip()
                groups[-1]['items'].append(f' - [bold]{target}:[/bold] {description}')

    groups = sorted(groups, key=lambda k: k['name'])

    for group in groups:
        console.print(f'\n{group["name"]}', style='bold green')
        for item in group['items']:
            console.print(item)
