"""
DigitalOcean Spaces storage client using boto3.

This module provides a simple interface for uploading and fetching objects
from DigitalOcean Spaces (S3-compatible object storage).
"""

import os
from typing import Optional

import boto3
from dotenv import load_dotenv


load_dotenv(override=True)


class DigitalOceanSpacesClient:
    """
    Client for interacting with DigitalOcean Spaces.

    This class provides methods to upload and fetch objects from DigitalOcean Spaces
    using the boto3 S3 client.

    Attributes
    ----------
    region : str
        The DigitalOcean Spaces region (e.g., 'nyc3', 'sfo3')
    bucket : str
        The name of the Spaces bucket
    endpoint : str
        The endpoint URL for the Spaces region
    client : boto3.client
        The boto3 S3 client instance

    Examples
    --------
    Initialize the client:

    >>> client = DigitalOceanSpacesClient(
    ...     region='nyc3',
    ...     bucket='my-bucket',
    ...     api_key='your-api-key',
    ...     secret_key='your-secret-key'
    ... )

    Upload a file object:

    >>> with open('image.png', 'rb') as f:
    ...     url = client.upload_fileobj(
    ...         file_obj=f,
    ...         object_name='users/123/logo/image.png',
    ...         content_type='image/png',
    ...         acl='public-read'
    ...     )
    ...     print(url)
    'https://nyc3.digitaloceanspaces.com/my-bucket/users/123/logo/image.png'

    Fetch an object:

    >>> obj = client.fetch_object('users/123/logo/image.png')
    >>> with open('downloaded.png', 'wb') as f:
    ...     f.write(obj['Body'].read())
    """

    def __init__(
        self,
        region: Optional[str] = None,
        bucket: Optional[str] = None,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
    ):
        """
        Initialize the DigitalOcean Spaces client.

        Parameters
        ----------
        region : str, optional
            The DigitalOcean Spaces region. Defaults to SPACES_REGION env var.
        bucket : str, optional
            The bucket name. Defaults to SPACES_BUCKET env var.
        api_key : str, optional
            The Spaces API key. Defaults to SPACES_API_KEY env var.
        secret_key : str, optional
            The Spaces secret key. Defaults to SPACES_SECRET_KEY env var.

        Raises
        ------
        ValueError
            If required parameters are not provided via arguments or environment variables.
        """
        self.region = region or os.getenv("SPACES_REGION")
        self.bucket = bucket or os.getenv("SPACES_BUCKET")
        api_key = api_key or os.getenv("SPACES_API_KEY")
        secret_key = secret_key or os.getenv("SPACES_SECRET_KEY")

        if not all([self.region, self.bucket, api_key, secret_key]):
            raise ValueError(
                "Missing required parameters. Provide region, bucket, api_key, and secret_key "
                "either as arguments or via environment variables: "
                "SPACES_REGION, SPACES_BUCKET, SPACES_API_KEY, SPACES_SECRET_KEY"
            )

        self.endpoint = f"https://{self.region}.digitaloceanspaces.com"

        self.client = boto3.client(
            "s3",
            region_name=self.region,
            endpoint_url=self.endpoint,
            aws_access_key_id=api_key,
            aws_secret_access_key=secret_key,
        )

    def upload_fileobj(
        self,
        file_obj,
        object_name: str,
        content_type: Optional[str] = None,
        acl: str = "public-read",
    ) -> str:
        """
        Upload a file object to DigitalOcean Spaces.

        Parameters
        ----------
        file_obj : file-like object
            The file object to upload (must have read() method)
        object_name : str
            The destination object name/path in the bucket (e.g., 'users/123/logo/image.png')
        content_type : str, optional
            The MIME type of the file (e.g., 'image/png', 'image/jpeg')
        acl : str, optional
            The access control list. Defaults to 'public-read'.
            Options: 'private', 'public-read', 'public-read-write', 'authenticated-read'

        Returns
        -------
        str
            The public URL of the uploaded object

        Examples
        --------
        >>> with open('logo.png', 'rb') as f:
        ...     url = client.upload_fileobj(
        ...         file_obj=f,
        ...         object_name='users/123/logo/header_logo.png',
        ...         content_type='image/png'
        ...     )
        """
        extra_args = {"ACL": acl}
        if content_type:
            extra_args["ContentType"] = content_type

        self.client.upload_fileobj(file_obj, self.bucket, object_name, ExtraArgs=extra_args)

        # Return public URL
        return f"{self.endpoint}/{self.bucket}/{object_name}"

    def fetch_object(self, object_name: str) -> dict:
        """
        Fetch an object from DigitalOcean Spaces.

        Parameters
        ----------
        object_name : str
            The object name/path in the bucket to fetch

        Returns
        -------
        dict
            A dictionary containing the object metadata and body stream.
            Access the file content with response['Body'].read()

        Examples
        --------
        >>> obj = client.fetch_object('users/123/logo/image.png')
        >>> content = obj['Body'].read()
        >>> metadata = obj['Metadata']
        >>> content_type = obj['ContentType']
        """
        return self.client.get_object(Bucket=self.bucket, Key=object_name)

    def get_public_url(self, object_name: str) -> str:
        """
        Get the public URL for an object without fetching it.

        Parameters
        ----------
        object_name : str
            The object name/path in the bucket

        Returns
        -------
        str
            The public URL of the object

        Examples
        --------
        >>> url = client.get_public_url('users/123/logo/image.png')
        >>> print(url)
        'https://nyc3.digitaloceanspaces.com/my-bucket/users/123/logo/image.png'
        """
        return f"{self.endpoint}/{self.bucket}/{object_name}"
