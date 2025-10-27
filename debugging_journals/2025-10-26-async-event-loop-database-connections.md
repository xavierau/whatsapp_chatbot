# Event Loop and Database Connection Issue in Expense Tools

**Date**: 2025-10-26
**Issue**: RuntimeError when expense_tools called from DSPy ReAct (async context)
**Status**: ✅ RESOLVED
**Related Files**: 
- `src/infrastructure/llm/tools/expenses.py:850-877`
- `src/infrastructure/database/session.py`

## Issue Description

When `expense_tools` is called from DSPy's ReAct module (which runs in an async context), we encounter:

```
RuntimeError: Task got Future attached to a different loop
RuntimeError: asyncio.run() cannot be called from a running event loop
```

## Root Cause Analysis

### The Problem

1. **DSPy ReAct runs in async context**: The ReAct module uses asyncio internally
2. **ThreadPoolExecutor creates new loop**: Our code detects the running loop and creates a new one in a thread
3. **Database connections tied to loop**: SQLAlchemy async connections are tied to the event loop they were created in
4. **Connection pool confusion**: The global engine's connection pool tries to reuse connections from different loops

### Why This Happens

```python
# Main event loop (DSPy)
async def react_loop():
    # Calls expense_tools (sync)
    expense_tools("list")
    
# expense_tools detects running loop
def expense_tools():
    asyncio.get_running_loop()  # ✓ Finds DSPy's loop
    
    # Creates new thread with new loop
    def _run_in_thread():
        new_loop = asyncio.new_event_loop()  # New loop in thread
        session = _session_factory()  # ❌ Session from main loop's engine!
        # Connections created in new_loop but pool thinks they're in main loop
```

## Attempted Solutions

### Solution 1: Use ThreadPoolExecutor (Current - FAILS)
- **Approach**: Detect running loop, create new thread with new loop
- **Issue**: Database connections tied to wrong loop
- **Result**: RuntimeError about different loops

### Solution 2: Use asyncio.run() (FAILS in async context)
- **Approach**: Just call asyncio.run(_execute())
- **Issue**: Can't call asyncio.run() when loop already running
- **Result**: RuntimeError: asyncio.run() cannot be called from a running event loop

## Correct Solution

### Option A: Create Engine Per Thread (Complex)
Create a new engine for each thread's event loop:

```python
def _run_in_thread():
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    try:
        # Create new engine for this loop
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        engine = create_async_engine(settings.database_url)
        session_factory = async_sessionmaker(engine)
        
        # Execute with this session factory
        result = new_loop.run_until_complete(_execute(session_factory))
        
        # Cleanup
        new_loop.run_until_complete(engine.dispose())
        return result
    finally:
        new_loop.close()
```

**Pros**: Isolates everything
**Cons**: Creates/destroys engine per call (expensive)

### Option B: Use nest_asyncio (Recommended)
Allow nested event loops:

```python
import nest_asyncio
nest_asyncio.apply()

# Now can call from within async context
result = asyncio.run(_execute())
```

**Pros**: Simple, works with existing code
**Cons**: Requires additional dependency

### Option C: Make Tool Truly Async (Best but Breaking)
Make expense_tools async and let DSPy handle it:

```python
async def expense_tools(operation: str, **kwargs: Any) -> str:
    # No event loop juggling needed
    return await _execute()
```

**Pros**: Cleanest, most efficient
**Cons**: DSPy might not support async tools (need to verify)

## Decision

Going with **Option B** (nest_asyncio) because:
1. Simple to implement
2. No architectural changes needed
3. Works with existing DSPy
4. Minimal performance impact
5. Already a common pattern in async Python

## Implementation

```python
# At top of expenses.py
import nest_asyncio
nest_asyncio.apply()

# In expense_tools
try:
    # No need to detect loop or use threads
    result = asyncio.run(_execute())
    return result
except Exception as e:
    ...
```

## Prevention Strategies

1. **Document async requirements**: Clearly state tools must handle nested async
2. **Test in async contexts**: Always test tools from within async event loops
3. **Consider async-first design**: Make tools async by default
4. **Use nest_asyncio by default**: Apply it globally for all async tools

## Related Issues

- Note tools likely have same issue but haven't been tested from async context
- Any tool using async database operations will face this

## Next Steps

1. Install nest_asyncio
2. Apply to expense_tools
3. Test from both sync and async contexts
4. Update note_tools with same fix
5. Document pattern for future tools

## Resolution

**Solution Implemented**: Option B (nest_asyncio)

### Changes Made

1. **Added dependency**: `uv add nest-asyncio`

2. **Updated `src/infrastructure/llm/tools/expenses.py`**:
   ```python
   import nest_asyncio
   
   # Apply at module level
   nest_asyncio.apply()
   
   # Simplified event loop handling
   def expense_tools(operation: str, **kwargs: Any) -> str:
       async def _execute():
           # ... async implementation
       
       # Now works from any context!
       result = asyncio.run(_execute())
       return result
   ```

3. **Removed complex ThreadPoolExecutor code**: No longer needed

### Testing

```bash
uv run python test_expense_integration_quick.py
```

**Result**: ✅ All tests pass
- Works from sync context (direct Python script)
- Works from async context (DSPy ReAct module)
- No more event loop errors
- Database connections properly managed

### Benefits

1. **Simpler code**: Removed 20+ lines of complex event loop juggling
2. **More reliable**: Single code path for all contexts
3. **Better performance**: No thread creation overhead
4. **Easier to maintain**: Standard asyncio.run() pattern
5. **Future-proof**: Works with any DSPy updates

### Verification

The fix was verified to work in:
- ✅ Direct sync calls: `expense_tools("create", ...)`
- ✅ DSPy Tool wrapper: `dspy.Tool(expense_tools)`
- ✅ ConversationAgent (sync): `agent.generate_response()`
- ✅ ConversationAgent (async): `await agent.agenerate_response()`

## Lessons Learned

1. **nest_asyncio is the standard solution** for nested event loop issues
2. **Complex workarounds** (ThreadPoolExecutor) often indicate missing the simple solution
3. **Database connections** are tightly coupled to event loops - can't easily move between loops
4. **Test in production-like environment**: DSPy's async context wasn't caught in unit tests
5. **Document assumptions**: Tools should document if they require sync/async contexts

## Prevention for Future Tools

1. **Default to nest_asyncio**: Apply it in all async tools
2. **Test from async context**: Always test tools from within async event loops
3. **Template pattern**: Use expense_tools as reference for new tools
4. **Document requirements**: State in docstring if tool supports async contexts

## Code Pattern for Future Reference

```python
# Standard pattern for DSPy tools with async operations
import asyncio
import nest_asyncio

# Apply once at module level
nest_asyncio.apply()

def my_tool(operation: str, **kwargs) -> str:
    """Tool that works in both sync and async contexts."""
    
    async def _execute():
        # Your async implementation here
        async with get_session() as session:
            # Database operations
            pass
    
    # Simple, reliable execution
    result = asyncio.run(_execute())
    return result
```

This pattern ensures the tool works reliably whether called from:
- Plain Python scripts
- Jupyter notebooks
- FastAPI endpoints
- DSPy ReAct modules
- Any other async framework
