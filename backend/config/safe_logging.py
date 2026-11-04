"""Server exception diagnostics without request data or exception messages."""
import logging
import traceback


class SafeExceptionFormatter(logging.Formatter):
    def format(self, record):
        lines = [f"{record.levelname} {record.name} status={getattr(record, 'status_code', '-')}"]
        if record.exc_info:
            error = record.exc_info[1]
            seen = set()
            while error is not None and id(error) not in seen:
                seen.add(id(error))
                lines.append(type(error).__name__)
                sqlstate = getattr(error, "sqlstate", None) or getattr(error, "pgcode", None)
                if isinstance(sqlstate, str) and len(sqlstate) == 5 and sqlstate.isalnum():
                    lines.append(f"SQLSTATE={sqlstate}")
                for frame in traceback.extract_tb(error.__traceback__):
                    lines.append(f"  {frame.filename}:{frame.lineno} in {frame.name}")
                error = error.__cause__ or (None if error.__suppress_context__ else error.__context__)
        return "\n".join(lines)
