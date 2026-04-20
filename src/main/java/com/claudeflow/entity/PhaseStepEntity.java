package com.claudeflow.entity;

import javax.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;

/**
 * 阶段步骤实体
 */
@Data
@Entity
@Table(name = "cf01_phase_step")
public class PhaseStepEntity {

    @Id
    @Column(length = 36)
    private String id;

    @Column(length = 36, nullable = false)
    private String taskId;

    @Column(length = 50, nullable = false)
    private String phase;

    @Column(nullable = false)
    private Integer stepIndex;

    @Column(length = 100)
    private String stepName;

    @Column(length = 20)
    private String status;

    @Column
    private LocalDateTime gmtCreate;

    @Column
    private LocalDateTime gmtModified;

    @PrePersist
    public void prePersist() {
        this.gmtCreate = LocalDateTime.now();
        this.gmtModified = LocalDateTime.now();
        if (this.status == null) {
            this.status = "pending";
        }
    }

    @PreUpdate
    public void preUpdate() {
        this.gmtModified = LocalDateTime.now();
    }
}