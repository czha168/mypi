from __future__ import annotations
import asyncio
import logging
from pathlib import Path
from codepi.core.session_manager import SessionManager

logger = logging.getLogger(__name__)


class RecoveryManager:
    """Manages recovery from rate-limited sessions."""
    
    def __init__(self, sessions_dir: Path):
        self.sessions_dir = Path(sessions_dir)
        self.session_manager = SessionManager(sessions_dir)
    
    async def recover_session(self, session_id: str) -> bool:
        """Attempt to recover a session that hit rate limits."""
        try:
            self.session_manager.load_session(session_id)
        except FileNotFoundError:
            logger.error(f"Session {session_id} not found")
            return False
        
        checkpoint = self.session_manager.get_last_recovery_checkpoint()
        if checkpoint is None:
            logger.info(f"Session {session_id} has no recovery checkpoint")
            return False
        
        retry_after = checkpoint.data.get("retry_after", 60)
        reason = checkpoint.data.get("reason", "Unknown error")
        
        logger.info(f"Recovering session {session_id} after rate limit")
        logger.info(f"Reason: {reason}")
        logger.info(f"Waiting {retry_after}s before retry...")
        
        await asyncio.sleep(retry_after)
        return True
    
    def list_sessions_needing_recovery(self) -> list[str]:
        """List all sessions with unresolved recovery checkpoints."""
        sessions = SessionManager.list_sessions(self.sessions_dir)
        needing_recovery = []
        
        for session_id in sessions:
            try:
                self.session_manager.load_session(session_id)
                if self.session_manager.get_last_recovery_checkpoint():
                    needing_recovery.append(session_id)
            except Exception as e:
                logger.warning(f"Error checking session {session_id}: {e}")
        
        return needing_recovery
