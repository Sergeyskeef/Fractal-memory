"""
CLI интерфейс для Fractal Memory.

Использует Rich для красивого вывода.
"""

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import typer

app = typer.Typer(
    name="fractal",
    help="Fractal Memory CLI — общение с AI агентом Марком"
)
console = Console()

BACKEND_URL = "http://localhost:8000"


def check_backend() -> bool:
    """Проверить доступность backend."""
    try:
        r = httpx.get(f"{BACKEND_URL}/health", timeout=5)
        return r.status_code == 200
    except:
        return False


@app.command()
def chat():
    """💬 Интерактивный чат с агентом."""
    
    if not check_backend():
        console.print("[red]❌ Backend недоступен. Запустите: docker compose up -d[/]")
        raise typer.Exit(1)
    
    # Получить имя агента
    try:
        health = httpx.get(f"{BACKEND_URL}/health").json()
        agent_name = health.get("agent", "Агент")
    except:
        agent_name = "Агент"
    
    console.print(Panel(
        f"🧠 [bold]{agent_name}[/] готов к общению\n"
        "[dim]Ctrl+C для выхода | /stats для статистики | /search <query> для поиска[/]",
    ))
    
    while True:
        try:
            message = console.input("\n[bold green]Вы:[/] ").strip()
            
            if not message:
                continue
            
            # Команды
            if message == "/stats":
                stats()
                continue
            if message.startswith("/search "):
                query = message[8:]
                search(query)
                continue
            if message == "/help":
                console.print("[dim]/stats — статистика | /search <query> — поиск | /consolidate — консолидация[/]")
                continue
            if message == "/consolidate":
                consolidate()
                continue
            
            # Отправить сообщение
            with console.status(f"[bold blue]{agent_name} думает...[/]"):
                response = httpx.post(
                    f"{BACKEND_URL}/chat",
                    json={"message": message},
                    timeout=60.0,
                )
            
            if response.status_code == 200:
                data = response.json()
                console.print(f"\n[bold blue]{agent_name}:[/] {data['response']}")
                console.print(
                    f"[dim](контекст: {data['context_count']}, "
                    f"важность: {data['importance']:.2f})[/]"
                )
            else:
                console.print(f"[red]Ошибка: {response.text}[/]")
                
        except KeyboardInterrupt:
            console.print("\n[yellow]👋 До свидания![/]")
            break
        except Exception as e:
            console.print(f"[red]Ошибка: {e}[/]")


@app.command()
def stats():
    """📊 Показать статистику памяти."""
    
    if not check_backend():
        console.print("[red]❌ Backend недоступен[/]")
        raise typer.Exit(1)
    
    try:
        response = httpx.get(f"{BACKEND_URL}/memory/stats")
        data = response.json()
        memory = data.get("memory", data)
        
        table = Table(title="📊 Статистика памяти")
        table.add_column("Уровень", style="cyan")
        table.add_column("Количество", style="green")
        table.add_column("Описание", style="dim")
        
        table.add_row("L0", str(memory.get("l0_size", 0)), "Working Memory (Redis)")
        table.add_row("L1", str(memory.get("l1_size", 0)), "Session Memory (Redis)")
        table.add_row("L2", str(memory.get("l2_count", 0)), "Episodic Memory (Graphiti)")
        table.add_row("L3", str(memory.get("l3_count", 0)), "Semantic Memory (Graphiti)")
        
        console.print(table)
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/]")


@app.command()
def search(query: str, limit: int = 10):
    """🔍 Поиск по памяти."""
    
    if not check_backend():
        console.print("[red]❌ Backend недоступен[/]")
        raise typer.Exit(1)
    
    try:
        response = httpx.post(
            f"{BACKEND_URL}/memory/search",
            json={"query": query, "limit": limit},
        )
        data = response.json()
        results = data.get("results", [])
        
        console.print(f"\n[bold]Найдено: {len(results)} результатов для '{query}'[/]\n")
        
        for i, result in enumerate(results, 1):
            content = result.get("content", "")[:200]
            score = result.get("score", 0)
            source = result.get("source", "unknown")
            
            console.print(Panel(
                content,
                title=f"#{i} [{source}] score: {score:.2f}",
                border_style="blue" if source == "graphiti" else "green",
            ))
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/]")


@app.command()
def consolidate():
    """🔄 Запустить консолидацию памяти."""
    
    if not check_backend():
        console.print("[red]❌ Backend недоступен[/]")
        raise typer.Exit(1)
    
    try:
        with console.status("[bold]Консолидация...[/]"):
            response = httpx.post(f"{BACKEND_URL}/memory/consolidate", timeout=300)
        
        data = response.json()
        console.print(
            f"✅ L0→L1: {data.get('l0_to_l1', 0)}, "
            f"L1→L2: {data.get('l1_to_l2', 0)}"
        )
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/]")


@app.command()
def health():
    """🏥 Проверить статус системы."""
    
    try:
        response = httpx.get(f"{BACKEND_URL}/health", timeout=5)
        data = response.json()
        
        status = "🟢" if data.get("status") == "ok" else "🔴"
        console.print(f"{status} Backend: {data.get('status')}")
        console.print(f"   Agent: {data.get('agent', 'N/A')}")
        console.print(f"   User: {data.get('user', 'N/A')}")
        console.print(f"   Model: {data.get('model', 'N/A')}")
        
    except Exception as e:
        console.print(f"🔴 Backend недоступен: {e}")


if __name__ == "__main__":
    app()

