/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { SchedulingJobResponse } from '../models/SchedulingJobResponse';
import type { UpdateSchedulingRequest } from '../models/UpdateSchedulingRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class DefaultService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * Update Job Scheduling
     * @returns SchedulingJobResponse Successful Response
     * @throws ApiError
     */
    public updateJobSchedulingApiV1JobsJobIdSchedulingPatch({
        jobId,
        requestBody,
    }: {
        jobId: string,
        requestBody: UpdateSchedulingRequest,
    }): CancelablePromise<SchedulingJobResponse> {
        return this.httpRequest.request({
            method: 'PATCH',
            url: '/jobs/{job_id}/scheduling',
            path: {
                'job_id': jobId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
