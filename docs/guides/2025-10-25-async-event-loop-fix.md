# Async Event Loop Fix for note_tools

**Date**: 2025-10-25
**Issue**: RuntimeError and ValueError when using note_tools in async contexts
**Status**: ✅ Fixed (Updated for uvloop compatibility)

## Problem History

### Initial Issue: Jupyter Notebooks
When using `note_tools` in Jupyter notebooks:
```
RuntimeError: This event loop is already running
```

### Updated Issue: uvloop in FastAPI
When using `note_tools` in FastAPI with uvloop:
```
ValueError: Can't patch loop of type <class 'uvloop.Loop'>
```

Root causes:
1. Jupyter notebooks run in an async event loop
2. FastAPI uses uvloop for better performance
3. `nest_asyncio` cannot patch uvloop
4. `note_tools` is a synchronous function that needs to call async code

## Solution

We implemented a universal event loop handler that works with all async contexts:

1. **Detects the context**: Checks if an event loop is already running
2. **Uses ThreadPoolExecutor**: Runs async code in a separate thread when loop exists
3. **Falls back gracefully**: Uses regular `asyncio.run()` in sync contexts

### Code Changes

**File**: `src/infrastructure/llm/tools/notes.py`

```python
# Final solution (works with uvloop, Jupyter, and sync contexts)
try:
    loop = asyncio.get_running_loop()
    # Loop is already running (FastAPI with uvloop, Jupyter, etc.)
    # We cannot use asyncio.run() or nest_asyncio with uvloop
    # Instead, run the async operation in a separate thread
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(asyncio.run, _execute())
        result = future.result()
except RuntimeError:
    # No running loop (regular Python scripts)
    result = asyncio.run(_execute())
```

### Why This Works

1. **ThreadPoolExecutor**: Creates a new thread with its own event loop
2. **asyncio.run**: Works in the new thread because there's no event loop there
3. **future.result()**: Blocks until the async operation completes
4. **Universal compatibility**: Works with uvloop, asyncio, and Jupyter

## Testing

Verified the fix works in:
- ✅ Regular Python scripts
- ✅ Async Python scripts
- ✅ Jupyter notebooks
- ✅ IPython environments
- ✅ FastAPI with uvloop (production environment)
- ✅ FastAPI with standard asyncio

## Usage

No changes required! The fix is transparent:

```python
# Works in Jupyter notebook
note_tools(operation="create", title="Test", content="Content")

# Works in regular Python
note_tools(operation="list", limit=10)

# Works in async functions
async def my_function():
    result = note_tools(operation="search", query="test")
```

## Performance Considerations

### Thread Overhead
- Creating a thread has minimal overhead (~1-2ms)
- Acceptable for LLM tool calls which take seconds
- More robust than trying to patch event loops

### Alternative Approaches Considered

1. **nest_asyncio** (❌ Doesn't work with uvloop)
   - Cannot patch uvloop event loops
   - Only works with standard asyncio

2. **asyncio.create_task()** (❌ Doesn't block)
   - Returns immediately, doesn't wait for result
   - Not suitable for synchronous tool interface

3. **run_in_executor()** (❌ Complex)
   - Requires access to running loop
   - More complex error handling

4. **ThreadPoolExecutor** (✅ Best choice)
   - Works universally
   - Simple and predictable
   - Blocks until completion

## Related Issues

If you see embedding dimension errors, that's a separate issue related to:
- Gemini API returning different dimensions than expected
- Need to verify actual embedding dimensions from API

## References

- [uvloop documentation](https://github.com/MagicStack/uvloop)
- [ThreadPoolExecutor](https://docs.python.org/3/library/concurrent.futures.html#threadpoolexecutor)
- [Asyncio in Jupyter](https://ipython.readthedocs.io/en/stable/interactive/autoawait.html)
