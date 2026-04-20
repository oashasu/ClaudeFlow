package com.claudeflow.entity;

import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;

/**
 * Checkpoint实体
 */
@Data
@Entity
@Table(name = "cf01_checkpoint")
public class CheckpointEntity {

    @Id
    @Column(length = 36)
    private String id;

    @Column(length = 36, nullable = false)
    private String taskId;

    @Column(length = 50, nullable = false)
    private String phase;

    @Column
    private Integer stepIndex;

    @Column(columnDefinition = "TEXT")
    private String summary;

    @Column
    private LocalDateTime gmtCreate;

    @PrePersist
    public void prePersist() {
        this.gmtCreate = LocalDateTime.now();
        if (this.stepIndex == null) {
            this.stepIndex = 0;
        }
    }
}