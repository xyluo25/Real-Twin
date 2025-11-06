-- 4) Signal schema

CREATE TABLE signal.controller (
    controller_id BIGSERIAL PRIMARY KEY,
    node_id BIGINT NOT NULL UNIQUE REFERENCES network.node (node_id) ON DELETE CASCADE,
    control_type signal_control_type NOT NULL,
    cycle_length INTEGER,
    offset_seconds INTEGER DEFAULT 0,
    description TEXT
);

CREATE TABLE signal.phase (
    phase_id BIGSERIAL PRIMARY KEY,
    controller_id BIGINT NOT NULL REFERENCES signal.controller (controller_id) ON DELETE CASCADE,
    phase_no INTEGER NOT NULL,
    phase_type phase_type NOT NULL,
    green INTEGER NOT NULL CHECK (green >= 0),
    yellow INTEGER NOT NULL CHECK (yellow >= 0),
    all_red INTEGER NOT NULL CHECK (all_red >= 0),
    UNIQUE (controller_id, phase_no)
);

CREATE TABLE signal.phase_movement (
    phase_id BIGINT NOT NULL REFERENCES signal.phase (phase_id) ON DELETE CASCADE,
    is_protected BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (phase_id)
);

CREATE TABLE signal.detector (
    detector_id BIGSERIAL PRIMARY KEY,
    controller_id BIGINT NOT NULL REFERENCES signal.controller (controller_id) ON DELETE CASCADE,
    link_id BIGINT REFERENCES network.link (link_id) ON DELETE SET NULL,
    lane_id BIGINT REFERENCES network.lane (lane_id) ON DELETE SET NULL,
    location DOUBLE PRECISION,
    detection_type TEXT
);

CREATE TABLE signal.timing_plan (
    plan_id BIGSERIAL PRIMARY KEY,
    controller_id BIGINT NOT NULL REFERENCES signal.controller (controller_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    active_from TIME,
    active_to TIME,
    dow_mask BIT(7) DEFAULT B'1111111'
);

CREATE TABLE signal.timing_plan_phase (
    plan_id BIGINT NOT NULL REFERENCES signal.timing_plan (plan_id) ON DELETE CASCADE,
    phase_id BIGINT NOT NULL REFERENCES signal.phase (phase_id) ON DELETE CASCADE,
    green_s INTEGER,
    yellow_s INTEGER,
    all_red_s INTEGER,
    sequence_no INTEGER,
    PRIMARY KEY (plan_id, phase_id)
);