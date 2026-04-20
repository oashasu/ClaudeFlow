package com.claudeflow.service;

import com.claudeflow.dto.CheckpointDTO;
import com.claudeflow.dto.PhaseStepDTO;
import com.claudeflow.entity.CheckpointEntity;
import com.claudeflow.entity.PhaseStepEntity;
import com.claudeflow.repository.CheckpointRepository;
import com.claudeflow.repository.PhaseStepRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

/**
 * Checkpoint服务
 */
@Service
@RequiredArgsConstructor
public class CheckpointService {

    private final CheckpointRepository checkpointRepository;
    private final PhaseStepRepository phaseStepRepository;

    /**
     * 获取Checkpoint历史
     */
    public List<CheckpointDTO> getCheckpointHistory(String taskId) {
        List<CheckpointEntity> checkpoints = checkpointRepository.findByTaskIdOrderByGmtCreateDesc(taskId);

        return checkpoints.stream()
                .map(this::toDTO)
                .collect(Collectors.toList());
    }

    /**
     * 回退到Checkpoint
     */
    @Transactional
    public CheckpointDTO revertToCheckpoint(String checkpointId) {
        CheckpointEntity checkpoint = checkpointRepository.findById(checkpointId)
                .orElseThrow(() -> new RuntimeException("Checkpoint not found: " + checkpointId));

        // 标记为当前checkpoint（后续需要通知Python端执行实际回退）
        return toDTO(checkpoint);
    }

    /**
     * 获取阶段步骤列表
     */
    public List<PhaseStepDTO> getPhaseSteps(String taskId, String phase) {
        List<PhaseStepEntity> steps = phaseStepRepository.findByTaskIdAndPhaseOrderByStepIndex(taskId, phase);

        return steps.stream()
                .map(this::toStepDTO)
                .collect(Collectors.toList());
    }

    /**
     * Entity转DTO
     */
    private CheckpointDTO toDTO(CheckpointEntity entity) {
        CheckpointDTO dto = new CheckpointDTO();
        dto.setId(entity.getId());
        dto.setTaskId(entity.getTaskId());
        dto.setPhase(entity.getPhase());
        dto.setStepIndex(entity.getStepIndex());
        dto.setSummary(entity.getSummary());
        dto.setGmtCreate(entity.getGmtCreate());
        dto.setCurrent(false); // 后续逻辑判断
        return dto;
    }

    /**
     * Step Entity转DTO
     */
    private PhaseStepDTO toStepDTO(PhaseStepEntity entity) {
        PhaseStepDTO dto = new PhaseStepDTO();
        dto.setId(entity.getId());
        dto.setTaskId(entity.getTaskId());
        dto.setPhase(entity.getPhase());
        dto.setStepIndex(entity.getStepIndex());
        dto.setStepName(entity.getStepName());
        dto.setStatus(entity.getStatus());
        dto.setGmtCreate(entity.getGmtCreate());
        dto.setGmtModified(entity.getGmtModified());
        return dto;
    }
}