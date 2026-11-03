/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { SchedulingDataResponse } from './SchedulingDataResponse';
export type SchedulingJobResponse = {
    id: string;
    state: string;
    version: number;
    executionData: Record<string, any>;
    schedulingData: SchedulingDataResponse;
};

