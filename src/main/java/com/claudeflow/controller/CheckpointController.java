package com.claudeflow.controller;

import com.claudeflow.dto.CheckpointDTO;
import com.claudeflow.dto.PhaseStepDTO;
import com.claudeflow.service.CheckpointService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * Checkpoint REST控制器
 */
@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class CheckpointController {

    private final CheckpointService checkpointService;

    /**
     * Checkpoint历史
     */
    @GetMapping("/checkpoints/{taskId}")
    public List<CheckpointDTO> getCheckpointHistory(@PathVariable String taskId) {
        return checkpointService.getCheckpointHistory(taskId);
    }

    /**
     * 回退到Checkpoint
     */
    @PostMapping("/checkpoints/revert/{checkpointId}")
    public CheckpointDTO revertToCheckpoint(@PathVariable String checkpointId) {
        return checkpointService.revertToCheckpoint(checkpointId);
    }

    /**
     * 阶段步骤列表
     */
    @GetMapping("/steps/{taskId}/{phase}")
    public List<PhaseStepDTO> getPhaseSteps(
            @PathVariable String taskId,
            @PathVariable String phase) {
        return checkpointService.getPhaseSteps(taskId, phase);
    }
}